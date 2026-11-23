"""Turn the generated sound-effect files (tools/audio/sfx_plan.json) into game files under Content/Audio/Gen.

Per file: decode (ffmpeg), 48 kHz, mono (stereo where the plan says), DC removed and a zero-phase 20 Hz high-pass,
cut as the plan says (oneshot: the loudest event that still leaves the set's minimum length after it, from its onset;
tail: the wash after the loudest transient; loop: a crossfaded seamless loop), never shorter than the plan's 'min'.
Per variant set: one loudness for every variant (the loudest 400 ms of the K-weighted signal, BS.1770 momentary
loudness: the measure of MurderInc.Audio.GenFiles),
matched to the web sound the set plays over (its loudness, shifted by the plan's peak against the web peak, so a
layer meant to sit under the body keeps its place), or for a replace-only set to its own median; a set with
'under' sits that many dB under another set once both layer volumes of audio.json are counted (the silenced shots
under the open ones). A peak over 0.95 after levelling goes through the web game's soft clip. 24-bit WAV. Also
writes the clean-language bleep (a 1 kHz tone). docs/unreal/AUDIO.md section 6.

Usage: python3 tools/audio/sfx_process.py <raw dir with <name>.mp3|.wav> [out dir]
"""
import json
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wavtools as wt  # noqa: E402

RATE = 48000
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
CONTENT = os.path.join(ROOT, 'unreal/MurderInc/Content')


def decode(path, stereo):
    out = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '2' if stereo else '1', '-ar', str(RATE), '-'],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(out, dtype='<f4').astype(np.float64)
    return x.reshape(-1, 2) if stereo else x


def highpass(x, hz=20.0):
    """DC out and a zero-phase 2nd-order Butterworth-shaped high-pass (magnitude only), in the frequency domain."""
    def one(c):
        c = c - np.mean(c)
        n = 1 << int(np.ceil(np.log2(len(c) + RATE)))
        f = np.fft.rfftfreq(n, 1.0 / RATE)
        h = (f / hz) ** 2 / np.sqrt(1 + (f / hz) ** 4)
        return np.fft.irfft(np.fft.rfft(c, n) * h, n)[:len(c)]
    return one(x) if x.ndim == 1 else np.stack([one(x[:, i]) for i in range(x.shape[1])], axis=1)


def env_of(x):
    m = np.abs(x if x.ndim == 1 else x.mean(axis=1))
    win = int(0.003 * RATE)
    return np.convolve(m, np.ones(win) / win, mode='same')


def fit(y, n):
    """Pad with silence to n frames."""
    if len(y) >= n:
        return y
    pad = np.zeros((n - len(y),) + y.shape[1:])
    return np.concatenate([y, pad])


def oneshot(x, secs, minsecs):
    env = env_of(x)
    # The loudest event that leaves at least the minimum length after it (generators sometimes put the hit late).
    room = max(1, len(env) - int(minsecs * RATE))
    p = int(np.argmax(env[:room]))
    a = p
    stop = max(0, p - int(0.15 * RATE))
    while a > stop and env[a] > 0.05 * env[p]:
        a -= 1
    a = max(0, a - int(0.003 * RATE))
    y = fit(x[a:a + int(secs * RATE)].copy(), int(minsecs * RATE))
    n = len(y)
    f = int(0.4 * n)
    ramp = np.cos(np.linspace(0, np.pi / 2, f)) ** 2
    y[n - f:] *= ramp if y.ndim == 1 else ramp[:, None]
    y[:32] *= np.linspace(0, 1, 32) if y.ndim == 1 else np.linspace(0, 1, 32)[:, None]
    return y


def tail(x, secs, minsecs):
    env = env_of(x)
    n = int(secs * RATE)
    room = max(1, len(env) - n - int(0.06 * RATE))
    p = int(np.argmax(env[:room])) + int(0.06 * RATE)
    y = fit(x[p:p + n].copy(), int(minsecs * RATE))
    n = len(y)
    fi = int(0.02 * RATE)
    y[:fi] *= np.linspace(0, 1, fi) if y.ndim == 1 else np.linspace(0, 1, fi)[:, None]
    f = int(0.5 * n)
    ramp = np.cos(np.linspace(0, np.pi / 2, f)) ** 2
    y[n - f:] *= ramp if y.ndim == 1 else ramp[:, None]
    return y


def loop(x, secs, minsecs):
    n = int(secs * RATE)
    xf = int(0.5 * RATE)
    start = max(0, (len(x) - n - xf) // 2)
    seg = x[start:start + n + xf].copy()
    if len(seg) < n + xf:
        n = len(seg) - xf
    head, end = seg[:xf], seg[n:n + xf]
    t = np.linspace(0, np.pi / 2, xf)
    fin, fout = np.sin(t), np.cos(t)
    if seg.ndim > 1:
        fin, fout = fin[:, None], fout[:, None]
    y = seg[:n].copy()
    y[:xf] = head * fin + end * fout   # the end flows into the start: seamless when looped
    return y


def loudest(x, rate=RATE):
    """The loudest 400 ms window (100 ms hop) of the K-weighted signal (BS.1770 momentary loudness, the mean over the
    channels), in LUFS: the measure of MurderInc.Audio.GenFiles."""
    x = x if x.ndim > 1 else x[:, None]
    x = np.stack([wt._kweight48(x[:, c]) for c in range(x.shape[1])], axis=1)
    win, hop = int(0.4 * rate), int(0.1 * rate)
    best = 0.0
    f = 0
    while True:
        seg = x[f:f + win]
        best = max(best, float(np.mean(seg ** 2)))
        if f + win >= len(x):
            break
        f += hop
    return -0.691 + 10 * np.log10(best + 1e-20)


def soft(y):
    a = np.abs(y)
    return np.where(a <= 0.6, y, np.sign(y) * (0.6 + 0.4 * np.tanh((a - 0.6) / 0.4)))


def level(y, target):
    for _ in range(3):
        y = y * 10 ** ((target - loudest(y)) / 20)
        if np.max(np.abs(y)) > 0.95:
            y = soft(y)
    return y


def main():
    raw = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(CONTENT, 'Audio/Gen')
    os.makedirs(out, exist_ok=True)
    plan = json.load(open(os.path.join(HERE, 'sfx_plan.json')))['files']
    audio = json.load(open(os.path.join(CONTENT, 'Data/audio.json')))
    sounds = json.load(open(os.path.join(CONTENT, 'Data/audio_sounds.json')))['sounds']
    # Which web sound each set plays over, and the layer volume it plays at.
    web_of, vol_of = {}, {}
    for name, rep in audio['replace'].items():
        if name == 'about':
            continue
        for layer in rep['layers']:
            key = os.path.basename(layer['files'][0]).rsplit('_', 1)[0]
            web_of.setdefault(key, name if name in sounds else None)
            vol_of.setdefault(key, layer.get('vol', 1.0))

    def web_loudness(name):
        d = sounds.get(name)
        if not d:
            return None
        vals, peaks = [], []
        for i in range(d.get('variants', 1)):
            p = os.path.join(CONTENT, 'Audio/Web', f'{name}_{i + 1:02d}.wav')
            if os.path.exists(p):
                x, r = wt.read(p)
                x = wt.resample(x.mean(axis=1), r, RATE)
                vals.append(loudest(x))
                peaks.append(np.max(np.abs(x)))
        return (float(np.median(vals)), float(np.max(peaks))) if vals else None

    cut, targets, report = {}, {}, []
    for key, p in plan.items():
        ys = []
        for i in range(p['n']):
            name = f'{key}_{i + 1:02d}'
            src = next((os.path.join(raw, name + e) for e in ('.mp3', '.wav') if os.path.exists(os.path.join(raw, name + e))), None)
            if not src:
                print(f'missing {name}')
                continue
            x = highpass(decode(src, p.get('stereo', False)))
            y = {'oneshot': oneshot, 'tail': tail, 'loop': loop}[p['cut']](x, p['len'], p.get('min', 0.0))
            ys.append((name, y / (np.max(np.abs(y)) + 1e-12) * p['peak']))
        cut[key] = ys
    # Targets: the web sound's loudness (shifted by plan peak / web peak), else the set's own median.
    for key, p in plan.items():
        ys = cut[key]
        if not ys:
            continue
        own = float(np.median([loudest(y) for _, y in ys]))
        web = web_loudness(web_of.get(key)) if web_of.get(key) else None
        targets[key] = web[0] + 20 * np.log10(p['peak'] / max(web[1], 1e-6)) if web else own
    for key, p in plan.items():
        if 'under' in p and p['under']['set'] in targets and key in targets:
            ref = p['under']['set']
            # (target + 20 log vol) = (ref target + 20 log ref vol) - dB
            targets[key] = targets[ref] + 20 * np.log10(vol_of.get(ref, 1.0) / vol_of.get(key, 1.0)) - p['under']['db']
    made = 0
    for key, ys in cut.items():
        for name, y in ys:
            y = level(y, targets[key])
            wt.write24(os.path.join(out, name + '.wav'), y, RATE)
            mono = y if y.ndim == 1 else y.mean(axis=1)
            report.append((name, len(y) / RATE, loudest(y), wt.lufs(mono, RATE), 20 * np.log10(np.max(np.abs(y)) + 1e-12),
                           float(np.mean(mono))))
            made += 1
    t = np.arange(int(1.0 * RATE)) / RATE
    wt.write24(os.path.join(out, 'bleep_1k.wav'), 0.5 * np.sin(2 * np.pi * 1000 * t), RATE)
    for name, secs, ld, lu, pk, dc in report:
        print(f'{name:24s} {secs:5.2f} s  momentary max {ld:6.1f} LUFS  {lu:6.1f} LUFS  peak {pk:5.1f} dBFS  dc {dc:+.4f}')
    size = sum(os.path.getsize(os.path.join(out, f)) for f in os.listdir(out) if f.endswith('.wav'))
    print(f'SFX OK {made} files + bleep, {size / 1048576:.1f} MB -> {out}')


if __name__ == '__main__':
    main()
