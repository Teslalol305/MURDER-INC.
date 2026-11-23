"""Measure a rendered mix (the engine's Saved/Audio/engine_render.wav or the offline fight_mixdown.wav): length,
peak, integrated loudness (ITU-R BS.1770: K-weighted, gated, channel weights 1 for front and centre, 0 for the LFE,
1.41 for the surrounds), the loudest short-term (3 s) loudness, the channels that carry signal, the first sound, the
longest silent stretch, and the voice moments: for each line start, the momentary loudness of the 1.2 s after it
against the 1.5 s before it (how far the line stands out of the mix).

Usage: python3 tools/audio/render_report.py <wav> [--voice "0.3:inc_03,9.2:holla_02,..."] [--json out.json]
       Several wavs may be given; each is reported in turn. Needs numpy only (wavtools.py).
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wavtools as wt  # noqa: E402

WEIGHTS = {1: [1.0], 2: [1.0, 1.0], 6: [1.0, 1.0, 1.0, 0.0, 1.41, 1.41], 8: [1.0, 1.0, 1.0, 0.0, 1.41, 1.41, 1.41, 1.41]}


def db(v):
    return float(20 * np.log10(max(v, 1e-12)))


def k_power(x, rate):
    """Per-channel K-weighted signal (frames x channels)."""
    if rate != 48000:
        x = np.stack([wt.resample(x[:, c], rate, 48000) for c in range(x.shape[1])], axis=1)
    return np.stack([wt._kweight48(x[:, c]) for c in range(x.shape[1])], axis=1)


def block_loudness(y, w, block, hop):
    """Loudness of each block (LKFS) and the weighted mean squares."""
    n = len(y)
    if n < block:
        block = n
    zs = []
    for i in range(0, max(1, n - block + 1), hop):
        seg = y[i:i + block]
        zs.append(float(np.sum(w * np.mean(seg ** 2, axis=0))))
    zs = np.array(zs) if zs else np.array([0.0])
    return -0.691 + 10 * np.log10(zs + 1e-12), zs


def integrated(y, w):
    l, zs = block_loudness(y, w, 19200, 4800)
    zs = zs[l > -70]
    if len(zs) == 0:
        return -70.0
    rel = -0.691 + 10 * np.log10(np.mean(zs)) - 10
    l = -0.691 + 10 * np.log10(zs + 1e-12)
    zs = zs[l > rel]
    return float(-0.691 + 10 * np.log10(np.mean(zs) + 1e-12)) if len(zs) else -70.0


def momentary(y, w, t0, t1, rate=48000):
    a, b = max(0, int(t0 * rate)), min(len(y), int(t1 * rate))
    if b - a < 480:
        return -70.0
    seg = y[a:b]
    return float(-0.691 + 10 * np.log10(np.sum(w * np.mean(seg ** 2, axis=0)) + 1e-12))


def report(path, voice):
    x, rate = wt.read(path)
    frames, ch = x.shape
    secs = frames / rate
    w = np.array(WEIGHTS.get(ch, [1.0] * ch))
    peak = float(np.max(np.abs(x))) if frames else 0.0
    per_ch = [db(float(np.max(np.abs(x[:, c])))) if frames else -240.0 for c in range(ch)]
    y = k_power(x, rate) if frames else x
    out = {
        'file': path, 'seconds': round(secs, 3), 'rate': rate, 'channels': ch, 'bytes': os.path.getsize(path),
        'peak_dbfs': round(db(peak), 2), 'peak_per_channel_dbfs': [round(p, 1) for p in per_ch],
        'channels_with_signal': [c for c in range(ch) if per_ch[c] > -60],
    }
    if frames == 0 or peak < 1e-6:
        out.update({'integrated_lufs': -70.0, 'silent': True})
        return out
    out['integrated_lufs'] = round(integrated(y, w), 2)
    st, _ = block_loudness(y, w, 3 * 48000, 4800)
    out['short_term_max_lufs'] = round(float(np.max(st)), 2)
    mono = np.max(np.abs(x), axis=1)
    win = int(0.05 * rate)
    env = np.convolve(mono, np.ones(win) / win, mode='same')
    loud = np.where(env > 10 ** (-60 / 20))[0]
    out['first_sound_s'] = round(float(loud[0]) / rate, 3) if len(loud) else None
    quiet = env <= 10 ** (-60 / 20)
    run = best = 0
    for q in quiet[::win]:
        run = run + 1 if q else 0
        best = max(best, run)
    out['longest_silence_s'] = round(best * win / rate, 2)
    out['clipped_samples'] = int(np.sum(np.abs(x) >= 0.9999))
    moments = []
    for t, name in voice:
        after = momentary(y, w, t, t + 1.2)
        before = momentary(y, w, t - 1.5, t)
        moments.append({'t': t, 'line': name, 'after_lufs': round(after, 1), 'before_lufs': round(before, 1), 'rise_db': round(after - before, 1)})
    out['voice'] = moments
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('wav', nargs='+')
    ap.add_argument('--voice', default='')
    ap.add_argument('--json', default='')
    a = ap.parse_args()
    voice = []
    for item in filter(None, a.voice.split(',')):
        t, _, name = item.partition(':')
        voice.append((float(t.rstrip('s')), name.strip()))
    results = [report(p, voice) for p in a.wav]
    for r in results:
        print('%s: %.2f s, %d ch @ %d Hz, peak %.1f dBFS, integrated %.1f LUFS, short-term max %s LUFS, signal on channels %s, first sound %s s, longest silence %s s, %s clipped' % (
            os.path.basename(r['file']), r['seconds'], r['channels'], r['rate'], r['peak_dbfs'], r['integrated_lufs'], r.get('short_term_max_lufs'),
            r['channels_with_signal'], r.get('first_sound_s'), r.get('longest_silence_s'), r.get('clipped_samples')))
        for m in r.get('voice', []):
            print('  voice %6.1f s %-14s %6.1f LUFS after, %6.1f before, %+5.1f dB' % (m['t'], m['line'], m['after_lufs'], m['before_lufs'], m['rise_db']))
    if a.json:
        json.dump(results, open(a.json, 'w'), indent=1)


if __name__ == '__main__':
    main()
