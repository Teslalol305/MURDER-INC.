#!/usr/bin/env python3
# Do the music's stems keep time? Where is each of the seven stems in its own loop, window by window, in a recording
# of the stream (rtcaudio.py's sound.wav), and is it where the others are?
#
# The score's seven stems (stem_drums, _hats, _bass, _keys, _strings, _bell, _crackle: Content/Audio/Web/stem_*_01.wav,
# 20.87 s each) start together when a run begins and loop side by side for as long as the game runs: a stem that
# plays without a break is at the same place in its loop at the same moment as the others, so the moment at which its
# loop started on the recording's own clock (window time minus loop place, mod the loop) is the same number for every
# stem and for every window. Version 3b's game lost the stems' voices in a magazine dump (the engine had 32 voices and
# gave up the quietest), and each stem came back from the top of its loop at its own moment: from then on the drums,
# the bass and the hats were 0.2 and 0.3 s apart for the rest of the session, and the strings and the bell (at no
# volume until a fight lifts them, which the engine treated as "not playing") came in on the wrong bar. Nothing in the
# report's "no digital silence" looked at the music's time. This does.
#
#   python3 music_phase.py <run folder or sound.wav> [--audio <Content/Audio>] [--window 6] [--step 3]
#                          [--from s] [--to s] [--tol 0.02] [--json out.json] [--quiet]
#
# Method: each stem's file is band-limited to the band in which the stream keeps its waveform (the codec's) and tiled
# as a loop; a window of the band-limited recording is cross-correlated with it (FFT) over every place in the loop
# (the first window of a stem) or +-1.5 s around where the previous window said it was (a stem that is not where it was
# is looked for again over the whole loop). A find is a correlation of 0.12 or more that stands 0.05 or more above the
# best place more than 0.35 s from it (a tonal stem repeats itself every beat and bar, so the next best place is a
# beat away and not far below: the bass at 0.78 against 0.43 in a clean mix, 0.45 to 0.55 against 0.27 to 0.40 under
# gunfire, the numbers of the review of version 3b). A stem with no find in a window (the strings and the bell at no
# volume, the hats under the guns) is "not heard" there, which is not a fault.
#
# The verdict, per stem: its loop's start (on the recording's clock) in every window that heard it must be the start
# of the drums' loop in the first window that heard them, to within --tol seconds (default 20 ms: the codec and the
# correlation's grain are well under that). The game starts the seven stems once for the whole session and never stops
# them, so a stem that is anywhere else was restarted (the strings and the bell may only be heard in a fight: their
# first window is compared like any other). Exit status 0 when every stem keeps time with itself and with the drums, 2 when one does not,
# 1 when the recording could not be read or the drums were never heard. With rtcaudio.py's sound.wav.json beside the
# recording the windows are named by the script's markers ("say SND empty": the magazine fired empty).
#
# numpy only (the box's /opt/venv/bin/python3 has it; the viewer's venv has not). It takes every core for a few
# seconds a stem: run it after a run, never beside one.
import argparse
import json
import math
import os
import sys
import wave

import numpy as np

SR = 48000
STEMS = {   # name: the band that the stream keeps the waveform of and the stem has most in
    'drums': (150, 6000),
    'hats': (3000, 12000),
    'bass': (40, 400),
    'keys': (200, 3000),
    'strings': (200, 4000),
    'bell': (800, 8000),
    'crackle': (1000, 10000),
}


def read_wav(path):
    """(rate, mono float64) of a PCM 16/24/32-bit or 32-bit float WAV, channels averaged."""
    with open(path, 'rb') as f:
        b = f.read()
    if b[:4] != b'RIFF' or b[8:12] != b'WAVE':
        raise ValueError(f'{path}: not a WAV')
    i, fmt, data = 12, None, None
    while i + 8 <= len(b):
        tag, size = b[i:i + 4], int.from_bytes(b[i + 4:i + 8], 'little')
        if tag == b'fmt ':
            fmt = b[i + 8:i + 8 + size]
        elif tag == b'data':
            data = b[i + 8:i + 8 + size]
        i += 8 + size + (size & 1)
    kind, ch, rate = int.from_bytes(fmt[0:2], 'little'), int.from_bytes(fmt[2:4], 'little'), int.from_bytes(fmt[4:8], 'little')
    bits = int.from_bytes(fmt[14:16], 'little')
    if kind == 0xFFFE:
        kind = int.from_bytes(fmt[24:26], 'little')
    if kind == 3 and bits == 32:
        x = np.frombuffer(data, dtype='<f4').astype(np.float64)
    elif kind == 1 and bits == 16:
        x = np.frombuffer(data, dtype='<i2').astype(np.float64) / 32768.0
    elif kind == 1 and bits == 24:
        a = np.frombuffer(data[:len(data) // 3 * 3], dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        v = a[:, 0] | (a[:, 1] << 8) | (a[:, 2] << 16)
        x = np.where(v >= 1 << 23, v - (1 << 24), v) / float(1 << 23)
    elif kind == 1 and bits == 32:
        x = np.frombuffer(data, dtype='<i4').astype(np.float64) / 2147483648.0
    else:
        raise ValueError(f'{path}: WAV format {kind} with {bits} bits is not read')
    return rate, x[:len(x) // ch * ch].reshape(-1, ch).mean(axis=1)


def to48(x, rate):
    if rate == SR:
        return x
    n = int((len(x) - 1) * SR / rate)
    return np.interp(np.arange(n) * rate / SR, np.arange(len(x)), x)


def bandpass(x, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1.0 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x))


def correlate(r, loop, at, centre=None, span=None):
    """Where in the loop is the window r? The loop's place p of the window's first sample, the correlation there and how far
    it stands above the best place more than 0.35 s from it. centre/span: search only places within span seconds of
    centre (mod the loop)."""
    L = len(loop)
    n = len(r)
    if centre is None:
        reps = n // L + 3
        ref = np.tile(loop, reps)
        places = L
        base = 0   # ref[i + k] = loop[(i + k) mod L]: lag k is the place of the window's first sample
    else:
        pad = int(span * SR)
        reps = (n + 2 * pad) // L + 3
        ref = np.tile(loop, reps)
        base = int(round(centre * SR)) - pad
        base %= L
        ref = ref[base:base + n + 2 * pad]
        places = 2 * pad + 1
    size = 1 << int(math.ceil(math.log2(len(ref) + n)))
    C = np.fft.irfft(np.fft.rfft(ref, size) * np.conj(np.fft.rfft(r, size)), size)[:places]
    er = math.sqrt(float(np.dot(r, r))) + 1e-20
    cs = np.concatenate(([0.0], np.cumsum(ref * ref)))
    eref = np.sqrt(np.maximum(cs[n:n + places] - cs[:places], 0.0)) + 1e-20
    c = C / (er * eref)
    k = int(np.argmax(c))
    w = int(0.35 * SR)
    far = c.copy()
    if centre is None:   # the places wrap round the loop
        far[np.arange(k - w, k + w + 1) % len(c)] = -1.0
    else:
        far[max(0, k - w):k + w + 1] = -1.0
    margin = float(c[k]) - float(far.max())
    p = (base + k) % L if centre is not None else k
    return p / SR, float(c[k]), margin


def circ(d, loop_s):
    """d in seconds, brought into -loop/2 .. loop/2."""
    return (d + loop_s / 2) % loop_s - loop_s / 2


def analyse(rec_path, audio_dir, window=6.0, step=3.0, t_from=0.0, t_to=None, tol=0.02, log=print, min_corr=0.12, min_margin=0.05):
    rate, rec = read_wav(rec_path)
    if rate != SR:
        raise ValueError(f'{rec_path}: {rate} Hz, expected {SR}')
    seconds = len(rec) / SR
    t_to = min(t_to or seconds, seconds)
    starts = [t_from + k * step for k in range(int(max(0.0, (t_to - t_from - window)) / step) + 1)]
    out = {'recording': rec_path, 'seconds': round(seconds, 2), 'windows': starts, 'window': window, 'stems': {}}
    loops = {}
    for name, (lo, hi) in STEMS.items():
        path = os.path.join(audio_dir, 'Web', f'stem_{name}_01.wav')
        r, x = read_wav(path)
        x = to48(x, r)
        loops[name] = bandpass(np.tile(x, 3), lo, hi)[len(x):2 * len(x)]
        out.setdefault('loop', len(x) / SR)
    L = out['loop']
    for name, (lo, hi) in STEMS.items():
        log(f'{name}: band {lo}-{hi} Hz, {len(starts)} windows ...')
        band = bandpass(rec, lo, hi)
        rows, last = [], None
        for t in starts:
            a = int(t * SR)
            r = band[a:a + int(window * SR)]
            if len(r) < int(window * SR) * 0.9 or float(np.dot(r, r)) < 1e-9:
                rows.append({'t': t, 'heard': False, 'why': 'silence'})
                continue
            p = c = m = None
            if last is not None:   # the same place the previous window found, advanced by the time between them
                p, c, m = correlate(r, loops[name], a, centre=(last[0] + (t - last[1])) % L, span=1.5)
            if p is None or c < min_corr or m < min_margin:
                p, c, m = correlate(r, loops[name], a)
            heard = c >= min_corr and m >= min_margin
            row = {'t': t, 'heard': heard, 'place': round(p, 4), 'corr': round(c, 3), 'margin': round(m, 3)}
            if heard:
                row['start'] = round((t - p) % L, 4)   # where this stem's loop began on the recording's clock
                last = (p, t)
            rows.append(row)
        out['stems'][name] = rows
    # The verdict.
    heard = {n: [r for r in rows if r['heard']] for n, rows in out['stems'].items()}
    out['verdict'] = {}
    drums = heard.get('drums', [])
    if not drums:
        out['verdict']['error'] = 'the drums were never heard: nothing to compare with'
        return out
    # The reference is where the drums' loop began in the first window that heard them (the home screen, in the gate's
    # scripts): the stems are started once for the whole session and are never stopped, so every stem in every window
    # must still begin there. A restart of the drums themselves shows as the drums being off it.
    ref = drums[0]['start']
    out['reference'] = round(ref % L, 4)
    for n, hs in heard.items():
        if not hs:
            out['verdict'][n] = {'ok': True, 'heard': 0, 'note': 'not heard in any window (at no volume, or under the rest)'}
            continue
        offs = [circ(r['start'] - ref, L) for r in hs]
        med = float(np.median(offs))
        jumps = [(r['t'], round(1000 * o)) for r, o in zip(hs, offs) if abs(o) > tol]   # windows off the reference
        ok = not jumps
        out['verdict'][n] = {'ok': ok, 'heard': len(hs), 'of': len(starts), 'medianFromDrumsMs': round(1000 * med),
                             'jumps': jumps[:12], 'firstHeard': hs[0]['t'], 'lastHeard': hs[-1]['t']}
    # And the stems against each other in the same window (all of them jumping together is a restart of the whole
    # score, which the reference check calls out; the stems drifting apart is the fault of version 3b).
    spreads = []
    for k, t in enumerate(starts):
        offs = [circ(out['stems'][n][k]['start'] - ref, L) for n in STEMS if out['stems'][n][k].get('heard')]
        if len(offs) >= 2:
            spreads.append((t, round(1000 * (max(offs) - min(offs)))))
    out['spreads'] = spreads
    out['worstSpread'] = max(spreads, key=lambda x: x[1]) if spreads else None
    return out


def parts(rec_path):
    """The script's markers ("say SND <name>") of rtcaudio.py's sound.wav.json as (recording seconds, name), or []."""
    try:
        with open(rec_path + '.json') as f:
            m = json.load(f)
    except (OSError, ValueError):
        return []
    rows = [r for r in m.get('rows', []) if r.get('arrived') is not None]
    if not rows:
        return []
    arrived, at = np.array([r['arrived'] for r in rows]), np.array([r['at'] for r in rows])
    return [(float(np.interp(t, arrived, at)), line.split()[-1]) for t, line in m.get('actions', []) if line.startswith('say SND ')]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('recording', help='a run folder of lag-test.sh (its sound.wav) or a sound.wav')
    ap.add_argument('--audio', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'unreal', 'MurderInc', 'Content', 'Audio'))
    ap.add_argument('--window', type=float, default=6.0)
    ap.add_argument('--step', type=float, default=3.0)
    ap.add_argument('--tol', type=float, default=0.02)
    ap.add_argument('--from', dest='t_from', type=float, default=0.0)
    ap.add_argument('--to', dest='t_to', type=float, default=None)
    ap.add_argument('--json', default='')
    ap.add_argument('--quiet', action='store_true')
    A = ap.parse_args()
    path = os.path.join(A.recording, 'sound.wav') if os.path.isdir(A.recording) else A.recording
    try:
        res = analyse(path, A.audio, A.window, A.step, A.t_from, A.t_to, A.tol, log=(lambda *a: None) if A.quiet else print)
    except (OSError, ValueError, KeyError) as e:
        print(f'cannot read {path}: {e}')
        return 1
    if A.json:
        with open(A.json, 'w') as f:
            json.dump(res, f)
    marks = parts(path)

    def part_of(t):
        name = '-'
        for at, n in marks:
            if at <= t + res['window'] / 2:
                name = n
        return name

    print(f"{path}: {res['seconds']} s, windows of {res['window']} s every {A.step} s, loop {res.get('loop', 0):.4f} s")
    if 'error' in res.get('verdict', {}):
        print('NO VERDICT: ' + res['verdict']['error'])
        return 1
    print(f"the drums' loop began at {res['reference']:.3f} s of the recording in the first window that heard them: every stem in every window must still begin there, to within {1000 * A.tol:.0f} ms")
    names = list(STEMS)
    print('  window  part              ' + ' '.join(f'{n:>8s}' for n in names) + '   (ms from the drums; . not heard)')
    for k, t in enumerate(res['windows']):
        cells = []
        for n in names:
            r = res['stems'][n][k]
            if r['heard']:
                cells.append(f"{1000 * circ(r['start'] - res['reference'], res['loop']):+8.0f}")
            else:
                cells.append(f"{'.':>8s}")
        print(f'  {t:6.1f}  {part_of(t):16s}  ' + ' '.join(cells))
    bad = 0
    for n in names:
        v = res['verdict'][n]
        if v['heard'] == 0:
            print(f'{n:8s} not heard in any window')
            continue
        if v['ok']:
            print(f"{n:8s} in time with the drums in all {v['heard']} windows it was heard in (median {v['medianFromDrumsMs']:+d} ms, from {v['firstHeard']:.0f} s to {v['lastHeard']:.0f} s)")
        else:
            bad += 1
            where = ', '.join(f"{t:.0f} s: {ms:+d} ms" for t, ms in v['jumps'][:6])
            print(f"{n:8s} OUT OF TIME in {len(v['jumps'])} of {v['heard']} windows heard (median {v['medianFromDrumsMs']:+d} ms): {where}")
    w = res.get('worstSpread')
    apart = [t for t, ms in res.get('spreads', []) if ms > 1000 * A.tol]
    if w:
        print(f"the stems against each other in the same window: worst spread {w[1]} ms at {w[0]:.0f} s; "
              + (f"apart by more than {1000 * A.tol:.0f} ms in {len(apart)} of {len(res['spreads'])} windows" if apart else f"together (within {1000 * A.tol:.0f} ms) in all {len(res['spreads'])} windows with two stems or more"))
    if apart:
        bad += 1
    print('MUSIC IN TIME' if not bad else f'MUSIC OUT OF TIME: {bad} fault(s) (stems off the start of the drums, or apart from each other)')
    return 0 if not bad else 2


if __name__ == '__main__':
    sys.exit(main())
