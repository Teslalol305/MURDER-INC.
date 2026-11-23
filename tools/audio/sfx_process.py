"""Turn the generated sound-effect files (tools/audio/sfx_plan.json) into game files under Content/Audio/Gen:
decode (ffmpeg), 48 kHz, mono (stereo where the plan says), cut as the plan says (oneshot: the loudest event from its
onset; tail: the wash after the loudest transient; loop: a crossfaded seamless loop), peak-normalised to the web
sound's peak, 24-bit WAV. Also writes the clean-language bleep (a 1 kHz tone). docs/unreal/AUDIO.md section 6.

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


def decode(path, stereo):
    out = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '2' if stereo else '1', '-ar', str(RATE), '-'],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(out, dtype='<f4').astype(np.float64)
    return x.reshape(-1, 2) if stereo else x


def env_of(x):
    m = np.abs(x if x.ndim == 1 else x.mean(axis=1))
    win = int(0.003 * RATE)
    return np.convolve(m, np.ones(win) / win, mode='same')


def oneshot(x, secs):
    env = env_of(x)
    p = int(np.argmax(env))
    a = p
    stop = max(0, p - int(0.15 * RATE))
    while a > stop and env[a] > 0.05 * env[p]:
        a -= 1
    a = max(0, a - int(0.003 * RATE))
    y = x[a:a + int(secs * RATE)].copy()
    n = len(y)
    f = int(0.4 * n)
    ramp = np.cos(np.linspace(0, np.pi / 2, f)) ** 2
    y[n - f:] *= ramp if y.ndim == 1 else ramp[:, None]
    y[:32] *= np.linspace(0, 1, 32) if y.ndim == 1 else np.linspace(0, 1, 32)[:, None]
    return y


def tail(x, secs):
    env = env_of(x)
    n = int(secs * RATE)
    # The loudest transient where a full tail can still follow it (the model sometimes puts its hit late).
    room = max(1, len(env) - n - int(0.06 * RATE))
    p = int(np.argmax(env[:room])) + int(0.06 * RATE)
    y = x[p:p + n].copy()
    n = len(y)
    fi = int(0.02 * RATE)
    y[:fi] *= np.linspace(0, 1, fi)
    f = int(0.5 * n)
    y[n - f:] *= np.cos(np.linspace(0, np.pi / 2, f)) ** 2
    return y


def loop(x, secs):
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


def main():
    raw = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'unreal/MurderInc/Content/Audio/Gen')
    os.makedirs(out, exist_ok=True)
    plan = json.load(open(os.path.join(HERE, 'sfx_plan.json')))['files']
    made = 0
    for key, p in plan.items():
        for i in range(p['n']):
            name = f'{key}_{i + 1:02d}'
            src = next((os.path.join(raw, name + e) for e in ('.mp3', '.wav') if os.path.exists(os.path.join(raw, name + e))), None)
            if not src:
                print(f'missing {name}')
                continue
            x = decode(src, p.get('stereo', False))
            y = {'oneshot': oneshot, 'tail': tail, 'loop': loop}[p['cut']](x, p['len'])
            y = y / (np.max(np.abs(y)) + 1e-12) * p['peak']
            wt.write24(os.path.join(out, name + '.wav'), y, RATE)
            made += 1
    t = np.arange(int(1.0 * RATE)) / RATE
    wt.write24(os.path.join(out, 'bleep_1k.wav'), 0.5 * np.sin(2 * np.pi * 1000 * t), RATE)
    size = sum(os.path.getsize(os.path.join(out, f)) for f in os.listdir(out))
    print(f'SFX OK {made} files + bleep, {size / 1048576:.1f} MB -> {out}')


if __name__ == '__main__':
    main()
