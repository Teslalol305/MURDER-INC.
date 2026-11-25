# Is this sample of the game in that recording, where, and how strongly? The second half of the listening tool
# (rtcaudio.py records what a viewer receives; this file says what is in it). A loudness reading proves that
# something is heard; this proves that it is the game's own gun, step or voice line.
#
#   python3 audio_find.py <recording.wav> <source.wav> [<source.wav> ...] [options]
#   python3 audio_find.py <recording.wav> --library <Content/Audio> [--from s --to s]   every sample of the library, the found ones listed
#   python3 audio_find.py <selftest.wav> --truth <selftest-truth.json> --audio <Content/Audio>     checks the instrument (rtcaudio.py --selftest)
#
#   --from S, --to S      only this part of the recording (seconds on the sound's own clock)
#   --part NAME           only the part a viewer script marked: from its line "say <anything> NAME" to its next "say"
#                         line (the recording's .json has the times; sound-keys.txt marks every kind of sound so)
#   --rates A:B:STEP      playback speeds tried (default 0.955:1.045:0.0025: the game starts most sounds at a pitch
#                         jittered by up to 3.5 %, a faster sound being a shorter one); --rates 1 for music, voice and loops
#   --chunk S             seconds of the source used as the template, from --at S of the file (default 0.3 from 0: a
#                         shot's body; longer is surer for sounds played at their own speed, and wrong for jittered ones)
#   --min X               how far above chance a match must stand (default 1.5 times: see below)
#   --max N               occurrences listed per source (default 12)
#   --decoys N            also try N other samples of --audio that the game was not asked to play there, and print the
#                         strongest of them: what "not there" looks like in the same recording
#   --action TEXT         with the recording's .json (rtcaudio.py writes it): for every script line that starts with
#                         TEXT (for example "down 0", the fire button), the first occurrence after it and the delay:
#                         from the moment the viewer sent the input to the arrival of the packet that holds the
#                         sample's start (a browser plays it a little later: its own sound buffer comes on top)
#   --within S            ... looked for this long after the action (default 1.5)
#   --json FILE           the results as JSON
#
# How: a matched filter. The recording and the sample are brought to one band (150 Hz to 6 kHz, 16 kHz sampling: what
# an Opus stream and the game's own compression keep the waveform of). To find the sample, both are weighted by the
# inverse of the recording's own long-term spectrum (the textbook detector for a known signal in coloured noise), the
# sample is slid along the recording at each speed, and the score at a place is their correlation there. What chance
# gives is measured, not assumed, in two ways: the same sample at six speeds the game does not play it at (a quarter
# tone to a third off the speeds tried: the same spectrum and shape, out of tune with any music), and the same sample
# played backwards (a tone is the same backwards, and a note of the music matches any tone of its pitch: so a sample
# that is only a tone is never "found" in music, which is right). The best score of all those is the chance level. A
# place counts as a find when the sample scores 1.5 times that or more; "x chance" in the lines is that ratio (a
# sample that is there scores 2 to 50). For music and other long sounds played at their own speed, use a long
# template (--rates 1 --chunk 4): a tune is not itself backwards.
# For every find the plain numbers are then worked out at its place and speed: "score" is the correlation of the
# unweighted waveforms, from -1 to 1 (1: the recording is the sample alone there, 0.7: as much other sound as sample,
# 0.1: the sample 20 dB under the rest), and "gain" is the sample's amplitude in the recording against the file's own
# (in dB, on the mean of the two channels): what the mix did to it.
# Needs numpy (/opt/venv/bin/python3 on the box).
import argparse
import bisect
import glob
import json
import math
import os
import random
import struct
import sys

import numpy as np

RATE = 48000
DEC = 3
FS = RATE // DEC
BAND = (150.0, 6000.0)
PAD = 0.03   # seconds of nothing around a template, so the band filter's ringing belongs to it


def read_wav(path):
    """(rate, float array [frames, channels]) of a PCM (8 to 32 bit) or float WAV."""
    with open(path, 'rb') as f:
        b = f.read()
    if b[:4] != b'RIFF' or b[8:12] != b'WAVE':
        raise ValueError(f'{path}: not a WAV')
    i, fmt, data = 12, None, None
    while i + 8 <= len(b):
        tag, size = b[i:i + 4], struct.unpack('<I', b[i + 4:i + 8])[0]
        if tag == b'fmt ':
            fmt = b[i + 8:i + 8 + size]
        elif tag == b'data':
            data = b[i + 8:i + 8 + size]
        i += 8 + size + (size & 1)
    if fmt is None or data is None:
        raise ValueError(f'{path}: no fmt or data chunk')
    kind, ch, rate, _, _, bits = struct.unpack('<HHIIHH', fmt[:16])
    if kind == 0xFFFE:
        kind = struct.unpack('<H', fmt[24:26])[0]
    n = len(data) // (bits // 8 * ch)
    if kind == 3:
        x = np.frombuffer(data, dtype='<f4' if bits == 32 else '<f8', count=n * ch).astype(np.float64)
    elif kind == 1 and bits == 16:
        x = np.frombuffer(data, dtype='<i2', count=n * ch) / 32768.0
    elif kind == 1 and bits == 24:
        raw = np.frombuffer(data, dtype=np.uint8, count=n * ch * 3).reshape(-1, 3).astype(np.int32)
        v = raw[:, 0] | (raw[:, 1] << 8) | (raw[:, 2] << 16)
        x = np.where(v >= 1 << 23, v - (1 << 24), v) / float(1 << 23)
    elif kind == 1 and bits == 32:
        x = np.frombuffer(data, dtype='<i4', count=n * ch) / float(1 << 31)
    elif kind == 1 and bits == 8:
        x = (np.frombuffer(data, dtype=np.uint8, count=n * ch).astype(np.float64) - 128) / 128.0
    else:
        raise ValueError(f'{path}: WAV format {kind} with {bits} bits is not read')
    return rate, x.reshape(-1, ch)


def mono48(path):
    rate, x = read_wav(path)
    m = x.mean(axis=1)
    if rate != RATE:
        m = np.interp(np.arange(int(len(m) * RATE / rate)) * rate / RATE, np.arange(len(m)), m)
    return m


def band(x):
    """48 kHz to the analysis band at 16 kHz."""
    n = len(x)
    if n < 16:
        return np.zeros(0)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1.0 / RATE)
    X[(f < BAND[0]) | (f > BAND[1])] = 0
    return np.fft.irfft(X, n)[::DEC]


def rates_of(text):
    p = [float(v) for v in text.split(':')]
    if len(p) == 1:
        return [p[0]]
    a, b, step = p
    return [round(a + k * step, 5) for k in range(int(round((b - a) / step)) + 1)]


class Recording:
    def __init__(self, path, t_from=0.0, t_to=None, whole=None):
        self.path = path
        if whole is None:
            rate, whole = read_wav(path)
            if rate != RATE:
                raise ValueError(f'{path}: {rate} Hz, want {RATE}')
        self.whole = whole
        x = whole
        self.seconds = len(x) / RATE
        self.offset = max(0.0, t_from)
        a, b = int(self.offset * RATE), len(x) if t_to is None else min(len(x), int(t_to * RATE))
        self.raw = x[a:b]
        self.x = band(self.raw.mean(axis=1))
        self.n = len(self.x)
        self.size = 1 << int(math.ceil(math.log2(max(2, self.n + 8 * FS))))   # room for templates of up to eight seconds
        self.cum = np.concatenate(([0.0], np.cumsum(self.x * self.x)))
        # The weighting: one over the recording's long-term spectrum (frames of 64 ms that are not silent, smoothed
        # over 140 Hz so the weighting's own echo stays inside a template's padding), at most 20 dB of lift.
        size, hop = 1024, 512
        frames = [self.x[k:k + size] for k in range(0, max(0, self.n - size), hop)]
        frames = [f for f in frames if float(np.dot(f, f)) > size * 1e-9]
        if frames:
            power = np.mean([np.abs(np.fft.rfft(f * np.hanning(size))) ** 2 for f in frames], axis=0)
        else:
            power = np.ones(size // 2 + 1)
        power = np.convolve(power, np.ones(9) / 9, mode='same')
        f_small = np.fft.rfftfreq(size, 1.0 / FS)
        inside = (f_small >= BAND[0]) & (f_small <= BAND[1])
        power = np.maximum(power, power[inside].max() * 1e-2)
        weight = np.where(inside, 1.0 / np.sqrt(power), 0.0)
        self.W = np.interp(np.fft.rfftfreq(self.size, 1.0 / FS), f_small, weight)
        self.Xw = np.fft.rfft(self.x, self.size) * self.W
        xw = np.fft.irfft(self.Xw, self.size)[:self.n]
        self.cumw = np.concatenate(([0.0], np.cumsum(xw * xw)))
        self.meta, self.keys, self.times = None, None, None
        if os.path.exists(path + '.json'):
            with open(path + '.json') as f:
                self.meta = json.load(f)

    def cut(self, t_from, t_to):
        """A part of this recording (the file is not read again)."""
        r = Recording(self.path, t_from, t_to, whole=self.whole)
        r.meta = self.meta
        return r

    def media(self, wall):
        """The place on the sound's clock (seconds) of the first packet that arrived at or after that wall time."""
        packets = self.meta and self.meta.get('packets')
        if not packets:
            return None
        if self.times is None:
            self.times = [p[1] for p in packets]
        i = min(len(packets) - 1, bisect.bisect_left(self.times, wall))
        return packets[i][0] / RATE

    def part(self, name):
        """(from, to) on the sound's clock of the part a viewer script marked with "say ... <name>": from that line to
        the next "say" line."""
        says = [(t, line) for t, line in (self.meta or {}).get('actions', []) if line.startswith('say ')]
        for k, (t, line) in enumerate(says):
            if line.split()[-1] == name:
                end = says[k + 1][0] if k + 1 < len(says) else float('inf')
                a, b = self.media(t), self.media(end) if end != float('inf') else self.seconds
                return a, b
        return None

    def arrival(self, seconds):
        """When the packet that holds that moment of the sound arrived at the viewer (rtcaudio.py's clock, the one its
        script lines are timed on), or None without the recording's .json."""
        packets = self.meta and self.meta.get('packets')
        if not packets:
            return None
        if self.keys is None:
            self.keys = [p[0] for p in packets]
        i = max(0, bisect.bisect_right(self.keys, seconds * RATE) - 1)
        return packets[i][1]


def template(seg, r):
    """The source's chunk played at speed r, in the analysis band, with PAD of nothing before and after."""
    pad48 = int(PAD * RATE)
    m = int(len(seg) / r)
    y = np.interp(np.arange(m) * r, np.arange(len(seg)), seg)
    return band(np.concatenate((np.zeros(pad48), y, np.zeros(pad48))))


def scores(rec, seg, r):
    """The weighted score of the chunk at speed r at every place of the recording (0 where the recording is silent)."""
    t = template(seg, r)
    M = len(t)
    if M >= rec.n or M + rec.n > rec.size:
        return None
    Tw = np.fft.rfft(t, rec.size) * rec.W
    tw = np.fft.irfft(Tw, rec.size)
    et = float(np.dot(tw, tw))
    if et <= 0:
        return None
    c = np.fft.irfft(rec.Xw * np.conj(Tw), rec.size)[:rec.n - M + 1]
    er = rec.cumw[M:M + len(c)] - rec.cumw[:len(c)]
    # Where the recording is silent (under about -75 dBFS over the template's length) there is nothing to find.
    heard = (rec.cum[M:M + len(c)] - rec.cum[:len(c)]) > M * 3e-8
    return np.where(heard, c / np.sqrt(et * er + 1e-30), 0.0)


def find(rec, src48, rates, chunk=0.3, at=0.0, min_x=1.5, max_n=12):
    """Occurrences of one source in the recording: a list of dicts (seconds, x, score, rate, gainDb), strongest first,
    then the strongest "x chance" anywhere (whether or not it is a find)."""
    seg = src48[int(at * RATE):int((at + chunk) * RATE)]
    if len(seg) < RATE // 50 or rec.n < FS // 10:
        return [], 0.0
    pad = int(PAD * RATE) // DEC
    best = np.zeros(rec.n)
    which = np.zeros(rec.n, dtype=np.int16)
    for k, r in enumerate(rates):
        s = scores(rec, seg, r)
        if s is None:
            continue
        # Place a score at the sample's own start (the template begins PAD before it).
        hi = min(rec.n, pad + len(s))
        part = s[:hi - pad]
        better = part > best[pad:hi]
        best[pad:hi] = np.where(better, part, best[pad:hi])
        which[pad:hi] = np.where(better, k, which[pad:hi])
    # Chance, measured two ways and the higher taken. The same chunk at speeds the game does not play it at, between
    # the notes of any music (one and a half, two and a half and three and a half semitones beyond the speeds tried):
    # the null for noises and transients. And the chunk backwards at every eighth speed: the null for tones, which a
    # note of the music matches at the right speed whatever instrument played it.
    chance = 0.0
    nulls = [(seg, min(rates) * v) for v in (0.917, 0.8655, 0.817)] + [(seg, max(rates) * v) for v in (1.0905, 1.1554, 1.2241)]
    nulls += [(seg[::-1], r) for r in sorted(set(rates[::8]) | {min(rates, key=lambda v: abs(v - 1.0))})]
    for chunk_, r in nulls:
        s = scores(rec, chunk_, r)
        if s is not None and len(s):
            chance = max(chance, float(s.max()))
    if chance <= 0:
        return [], 0.0
    out = []
    work = best.copy()
    guard = max(int(0.05 * FS), int(0.5 * min(chunk, len(seg) / RATE) * FS))
    top = float(work.max()) / chance if len(work) else 0.0
    while len(out) < max_n:
        i = int(np.argmax(work))
        v = float(work[i])
        if v / chance < min_x:
            break
        # The place to a fraction of the 16 kHz step: a parabola through the three scores around the best.
        frac = 0.0
        if 0 < i < rec.n - 1:
            a, b, c2 = best[i - 1], best[i], best[i + 1]
            den = a - 2 * b + c2
            if den < 0:
                frac = max(-0.5, min(0.5, 0.5 * (a - c2) / den))
        # The plain numbers at that place and speed.
        r = rates[int(which[i])]
        t = template(seg, r)
        n0 = i - pad
        w = rec.x[max(0, n0):n0 + len(t)]
        t = t[max(0, -n0):max(0, -n0) + len(w)]
        dot, et, er = float(np.dot(w, t)), float(np.dot(t, t)), float(np.dot(w, w))
        out.append({'seconds': round(rec.offset + (i + frac) / FS, 4), 'x': round(v / chance, 1),
                    'score': round(dot / math.sqrt(et * er + 1e-30), 3), 'rate': r,
                    'gainDb': round(20 * math.log10(max(1e-9, abs(dot) / (et + 1e-30))), 1)})
        work[max(0, i - guard):i + guard + 1] = 0.0
    return out, top


def describe(name, src_seconds, hits, top, min_x):
    if not hits:
        return f'{name} ({src_seconds:.2f} s): NOT FOUND (strongest {top:.2f} x chance: under {min_x:g})'
    h = hits[0]
    return (f"{name} ({src_seconds:.2f} s): FOUND {len(hits)} time(s), strongest at {h['seconds']:.3f} s: {h['x']:.1f} x chance, score {h['score']:.2f}, "
            f"speed {h['rate']:.4f}, gain {h['gainDb']:+.1f} dB")


def truth_check(rec, truth, audio, min_x):
    """rtcaudio.py --selftest sent known things: does this file find them where and as they were sent?"""
    ok = True

    def check(name, good, text):
        nonlocal ok
        ok = ok and good
        print(('PASS ' if good else 'FAIL ') + name + ': ' + text)

    left = rec.raw[:, 0]
    loud = np.nonzero(np.abs(left) > 0.02)[0]
    if not len(loud):
        print('FAIL: the recording is silent')
        return False
    shift = loud[0] / RATE - truth['tone']['from']     # the recording's clock against the sender's (Opus: 6.5 ms)
    print(f'the recording runs {shift * 1000:+.1f} ms behind the sender\'s clock (the tone\'s start; Opus itself delays by 6.5 ms)')
    rates = rates_of('0.955:1.045:0.0025')
    for p in truth['planted']:
        src = mono48(os.path.join(audio, p['file']))
        hits, top = find(Recording(rec.path, p['at'] - 0.5, p['at'] + 1.5), src, rates, min_x=min_x, max_n=1)
        want = p['at'] + shift
        if not hits:
            check(f"{p['file']} at {p['at']} s", False, f'not found (strongest {top:.2f} x chance)')
            continue
        h = hits[0]
        err_ms = (h['seconds'] - want) * 1000
        gain_err = h['gainDb'] - 20 * math.log10(p['gain'])
        check(f"{p['file']} at {p['at']} s, gain {20 * math.log10(p['gain']):+.1f} dB, speed {p['rate']}",
              abs(err_ms) <= 3 and abs(gain_err) <= 1.5 and abs(h['rate'] - p['rate']) <= 0.0051,
              f"found {err_ms:+.2f} ms from its place, gain {h['gainDb']:+.1f} dB ({gain_err:+.1f}), speed {h['rate']}, {h['x']} x chance, score {h['score']}")
    bed = truth.get('bed')
    if bed:
        src = mono48(os.path.join(audio, bed['file']))
        # A second and a half of it, from 0.9 s of the file: the stretch of the recording before the first planted shot.
        hits, top = find(Recording(rec.path, bed['from'], bed['from'] + 8.0), src, [1.0], chunk=1.5, at=0.9, min_x=min_x, max_n=12)
        want_db = 20 * math.log10(bed['gain'])
        here = [h for h in hits if abs(h['seconds'] - (bed['from'] + 0.9 + shift)) <= 0.003]
        good = bool(here) and abs(here[0]['gainDb'] - want_db) <= 1.5
        check(f"the music bed {bed['file']} from {bed['from']} s at {want_db:+.1f} dB", good,
              (f"found at its place: {here[0]['x']} x chance, gain {here[0]['gainDb']:+.1f} dB, score {here[0]['score']}" if here else describe('at its place', 1.5, [], top, min_x)))
    # What was not sent must not be found.
    for absent in ('Gen/explosion_near_01.wav', 'Voice/rule/murda_01.wav', 'Web/horn_far_01.wav'):
        path = os.path.join(audio, absent)
        if os.path.exists(path):
            hits, top = find(rec, mono48(path), rates, min_x=min_x, max_n=1)
            check(f'{absent}, which was not sent', not hits, f'strongest {top:.2f} x chance (a find is {min_x:g} or more)')
    # The delay from a script action to the sound it started.
    click = mono48(os.path.join(audio, truth['clickFile']))
    hits, top = find(Recording(rec.path, 15.0), click, [1.0], min_x=min_x, max_n=10)
    for a in truth['actions']:
        after = sorted(h['seconds'] for h in hits if rec.arrival(h['seconds']) is not None and rec.arrival(h['seconds']) >= a['sent'] - 0.01)
        if not after:
            check(f"the sample started by the action at {a['sent']:.3f} s", False, 'not found')
            continue
        measured = (rec.arrival(after[0]) - a['sent']) * 1000
        true = (a['frameLeft'] - a['sent']) * 1000
        place = (after[0] - (a['at'] + shift)) * 1000
        check(f"the delay from the action at {a['sent']:.3f} s to its sound", abs(measured - true) <= 8 and abs(place) <= 3,
              f"the packet with the sample's start arrived {measured:.0f} ms after the action; the sender handed that frame to its encoder {true:.0f} ms after it; "
              f"the sample was found {place:+.2f} ms from its place")
    print('SELFTEST PART 2 PASSED' if ok else 'SELFTEST PART 2 FAILED')
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('recording')
    ap.add_argument('sources', nargs='*')
    ap.add_argument('--library', default='')
    ap.add_argument('--audio', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'unreal', 'MurderInc', 'Content', 'Audio'))
    ap.add_argument('--part', default='')
    ap.add_argument('--from', dest='t_from', type=float, default=0.0)
    ap.add_argument('--to', dest='t_to', type=float, default=None)
    ap.add_argument('--rates', default='0.955:1.045:0.0025')
    ap.add_argument('--chunk', type=float, default=0.3)
    ap.add_argument('--at', type=float, default=0.0)
    ap.add_argument('--min', dest='min_x', type=float, default=1.5)
    ap.add_argument('--max', dest='max_n', type=int, default=12)
    ap.add_argument('--decoys', type=int, default=0)
    ap.add_argument('--action', default='')
    ap.add_argument('--within', type=float, default=1.5)
    ap.add_argument('--truth', default='')
    ap.add_argument('--json', default='')
    A = ap.parse_args()
    rec = Recording(A.recording, A.t_from, A.t_to)
    if A.part:
        span = rec.part(A.part)
        if span is None:
            sys.exit(f'no "say ... {A.part}" line in {A.recording}.json')
        A.t_from, A.t_to = span[0], span[1] + 0.5
        rec = rec.cut(A.t_from, A.t_to)
        print(f'part "{A.part}": {span[0]:.2f} to {span[1]:.2f} s of the sound')
    if A.truth:
        with open(A.truth) as f:
            sys.exit(0 if truth_check(rec, json.load(f), A.audio, A.min_x) else 1)
    rates = rates_of(A.rates)
    sources = list(A.sources)
    if A.library:
        sources += sorted(p for p in glob.glob(os.path.join(A.library, '**', '*.wav'), recursive=True) if not os.path.basename(p).startswith('IR_'))
    print(f'{A.recording}: {rec.seconds:.1f} s' + (f', searched from {rec.offset:g} s' if rec.offset or A.t_to else '') + (f' to {A.t_to:g} s' if A.t_to else '')
          + f'; {len(rates)} speed(s) from {rates[0]} to {rates[-1]}; template {A.chunk:g} s from {A.at:g} s of each file')
    results = {}
    for path in sources:
        full = path if os.path.exists(path) else os.path.join(A.audio, path)
        try:
            src = mono48(full)
        except (OSError, ValueError) as e:
            print(f'{path}: cannot be read ({e})')
            continue
        hits, top = find(rec, src, rates, A.chunk, A.at, A.min_x, A.max_n)
        name = os.path.relpath(full, A.audio) if os.path.abspath(full).startswith(os.path.abspath(A.audio)) else path
        results[name] = {'hits': hits, 'strongestXChance': round(top, 2)}
        if A.library and not hits:
            continue
        print(describe(name, len(src) / RATE, hits, top, A.min_x))
        for h in sorted(hits, key=lambda h: h['seconds']):
            w = rec.arrival(h['seconds'])
            print(f"    at {h['seconds']:9.3f} s" + (f" (arrived {w:8.3f})" if w is not None else '') + f"  {h['x']:5.1f} x chance  score {h['score']:.2f}  speed {h['rate']:.4f}  gain {h['gainDb']:+.1f} dB")
    if A.library:
        print(f"{sum(1 for r in results.values() if r['hits'])} of {len(results)} samples of the library found")
    if A.decoys:
        used = {os.path.abspath(p if os.path.exists(p) else os.path.join(A.audio, p)) for p in A.sources}
        pool = sorted(p for p in glob.glob(os.path.join(A.audio, '**', '*.wav'), recursive=True)
                      if os.path.abspath(p) not in used and not os.path.basename(p).startswith('IR_'))
        random.Random(7).shuffle(pool)
        worst = (0.0, '')
        found = []
        for p in pool[:A.decoys]:
            hits, top = find(rec, mono48(p), rates, A.chunk, A.at, A.min_x, 1)
            if top > worst[0]:
                worst = (top, os.path.relpath(p, A.audio))
            if hits:
                found.append(os.path.relpath(p, A.audio))
        print(f'{min(A.decoys, len(pool))} other samples of the library tried on the same part: strongest {worst[0]:.2f} x chance ({worst[1]})'
              + (f'; FOUND as well: {", ".join(found)} (they may be playing: the music and the street never stop)' if found else '; none found'))
        results['_decoys'] = {'tried': min(A.decoys, len(pool)), 'strongestXChance': round(worst[0], 2), 'strongest': worst[1], 'found': found}
    if A.action:
        actions = [(t, line) for t, line in (rec.meta or {}).get('actions', []) if line.startswith(A.action)]
        if not actions:
            print(f'no script line starting with "{A.action}" in {A.recording}.json')
        every = sorted((h['seconds'], name) for name, r in results.items() if not name.startswith('_') for h in r['hits'])
        delays = []
        for t, line in actions:
            first = next(((s, name) for s, name in every if rec.arrival(s) is not None and t - 0.005 <= rec.arrival(s) <= t + A.within), None)
            if first is None:
                print(f'action "{line}" at {t:.3f}: no occurrence within {A.within:g} s')
                continue
            d = (rec.arrival(first[0]) - t) * 1000
            delays.append(d)
            print(f'action "{line}" at {t:.3f}: the packet with the start of {first[1]} arrived {d:.0f} ms later (the start is at {first[0]:.3f} s of the sound)')
        if delays:
            delays.sort()
            print(f'delay from "{A.action}" sent to the arrival of its sound: {len(delays)} measured, shortest {delays[0]:.0f} ms, middle {delays[len(delays) // 2]:.0f} ms, longest {delays[-1]:.0f} ms')
            results['_delays'] = delays
    if A.json:
        with open(A.json, 'w') as f:
            json.dump(results, f, indent=1)


if __name__ == '__main__':
    main()
