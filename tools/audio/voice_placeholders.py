"""Build the PLACEHOLDER voice takes of voice.json from generated text-to-speech files (a generic stock voice,
not the character's voice). Every take is trimmed, folded to mono, resampled to 48 kHz, loudness-normalised to
-18 LUFS integrated with peaks under -1 dBFS, and written as 24-bit WAV under the name the real recording replaces
file for file (docs/unreal/AUDIO.md section 5). The crowd answer "R-U-L-E!" is assembled from several stock voices:
each voice's four letters are cut out and laid on one chant grid with small timing and pitch spreads, plus a short
room, three different mixes.

Usage: python3 tools/audio/voice_placeholders.py <raw dir> <plan.json> [out dir]
  plan.json: {"names": [...]} where names[i] is the take raw/<i>.wav becomes (holla_01, ..., crowd_a ...).
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wavtools as wt  # noqa: E402

RATE = 48000
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def mono(path):
    x, rate = wt.read(path)
    return wt.resample(x.mean(axis=1), rate, RATE)


def letters(x, want=4):
    """The `want` loudest syllables of a spelled take, in time order: (start, end) sample pairs."""
    win = int(RATE * 0.02)
    env = np.sqrt(np.convolve(x ** 2, np.ones(win) / win, mode='same'))
    on = env > 0.12 * env.max()
    # Bridge gaps shorter than 60 ms, then read off the runs.
    gap = int(0.06 * RATE)
    bridged = np.convolve(on.astype(np.float64), np.ones(gap), mode='same') > 0
    edges = np.diff(np.concatenate([[0], bridged.astype(np.int8), [0]]))
    starts, ends = np.where(edges == 1)[0], np.where(edges == -1)[0]
    segs = list(zip(starts, ends))
    segs = [s for s in segs if s[1] - s[0] > 0.06 * RATE]
    if len(segs) < want:
        return None
    segs = sorted(sorted(segs, key=lambda s: -np.sum(x[s[0]:s[1]] ** 2))[:want])
    pad = int(0.015 * RATE)
    return [(max(0, a - pad), min(len(x), b + int(0.05 * RATE))) for a, b in segs]


def room(x, seed):
    """A short, dense room so the crowd sounds like one space (exponential noise tail, 0.35 s)."""
    rng = np.random.default_rng(seed)
    n = int(0.35 * RATE)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / (0.07 * RATE))
    ir[0] = 0
    ir /= np.sqrt(np.sum(ir ** 2))
    m = 1 << int(np.ceil(np.log2(len(x) + n)))
    wet = np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(ir, m), m)[:len(x) + n]
    out = np.zeros(len(x) + n)
    out[:len(x)] += x
    return out + 0.35 * wet


def chant(voices, seed, grid=0.40, spread=0.03, detune=0.04):
    """Lay every voice's four letters on one grid: R . U . L . E (the last held a little longer)."""
    rng = np.random.default_rng(seed)
    times = [0.0, grid, 2 * grid, 3 * grid + 0.05]
    total = int((times[-1] + 1.2) * RATE)
    out = np.zeros(total)
    for v in voices:
        segs = letters(v)
        if not segs:
            continue
        gain = rng.uniform(0.6, 1.0)
        rate = 1.0 + rng.uniform(-detune, detune)
        for t, (a, b) in zip(times, segs):
            s = wt.resample(v[a:b], RATE, int(RATE / rate))
            at = int((t + rng.uniform(-spread, spread) + 0.03) * RATE)
            at = max(0, at)
            out[at:at + len(s)] += gain * s[:max(0, total - at)]
    return room(out, seed)


def main():
    raw, plan = sys.argv[1], sys.argv[2]
    out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(ROOT, 'unreal/MurderInc/Content/Audio/Voice/rule')
    os.makedirs(out, exist_ok=True)
    names = json.load(open(plan))['names']
    crowd = []
    report = []
    for i, name in enumerate(names):
        path = os.path.join(raw, f'{i}.wav')
        if not os.path.exists(path):
            print(f'missing {path}')
            continue
        x = mono(path)
        if name.startswith('crowd_'):
            crowd.append(wt.trim(x, RATE, threshold=0.05, pre=0.0, post=0.1))
            continue
        y = wt.normalise(wt.trim(x, RATE), RATE)
        wt.write24(os.path.join(out, f'{name}.wav'), y, RATE)
        report.append((name, len(y) / RATE, wt.lufs(y, RATE), 20 * np.log10(np.max(np.abs(y)))))
    # Three crowd answers from different voice subsets.
    subsets = [crowd, crowd[1:] + crowd[:1], crowd[::-1]]
    for k, subset in enumerate(subsets):
        if not subset:
            break
        y = wt.normalise(wt.trim(chant(subset, 17 + k), RATE, threshold=0.03), RATE, target=-17.0)
        name = f'rule_chant_{k + 1:02d}'
        wt.write24(os.path.join(out, f'{name}.wav'), y, RATE)
        report.append((name, len(y) / RATE, wt.lufs(y, RATE), 20 * np.log10(np.max(np.abs(y)))))
    for name, secs, l, p in report:
        print(f'{name:18s} {secs:5.2f} s  {l:6.1f} LUFS  peak {p:5.1f} dBFS')


if __name__ == '__main__':
    main()
