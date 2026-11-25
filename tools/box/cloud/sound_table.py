# Every sound the game started, looked for in what the viewer received: the table of a sound proof.
#
#   python3 sound_table.py <run folder of lag-test.sh ... audio=1 with the Development game> [--per 4] [--json out.json]
#
# The Development game, started with -LogCmds="LogMIAudioHost Verbose", writes one log line for every sound it starts
# on the audio device: the file, the sound's name, its category, the volume the game gave it, the mix gain of its
# category at that moment, the playback speed ("play Web/chopper_shot_02.wav sound=chopper_shot category=gun
# volume=0.953 mix=1.000 pitch=1.012"). The viewer's recording (rtcaudio.py: sound.wav, sound.wav.json) knows when
# every packet of sound arrived. This file takes each started sound (the first --per starts of every file), looks
# for that very sample at that speed in the second of recording that arrived after the log line (audio_find.py's
# matched filter), and prints per sound: how often the game started it, how many of the starts looked at were found,
# how far above chance, how loud against the file itself (and what the game's own numbers give: volume x category
# gain), and how long after the log line the packet with its first sample arrived.
#
# A start that is not found is not always a fault: a far 3D sound under a burst of gunfire, a pure tone under music of
# the same pitch (a steady tone is not told from chance: audio_find.py's header), a sound refused by the engine's voice
# limit. The table says so with "not found"; it never counts a packet as a sound.
# Needs numpy (/opt/venv/bin/python3 on the box).
import argparse
import calendar
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio_find as af  # noqa: E402

LINE = re.compile(r'\[(\d{4})\.(\d\d)\.(\d\d)-(\d\d)\.(\d\d)\.(\d\d):(\d{3})\].*LogMIAudioHost: Verbose: play (\S+) sound=(\S+) category=(\S+) '
                  r'volume=([\d.]+) mix=([\d.]+) pitch=([\d.]+)( 3d)?( loop)?')


def median(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if xs else float('nan')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('run')
    ap.add_argument('--audio', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'unreal', 'MurderInc', 'Content', 'Audio'))
    ap.add_argument('--per', type=int, default=4)
    ap.add_argument('--min', dest='min_x', type=float, default=1.5)
    ap.add_argument('--json', default='')
    A = ap.parse_args()
    rec = af.Recording(os.path.join(A.run, 'sound.wav'))
    if not rec.meta or not rec.meta.get('epoch') or not rec.meta.get('packets'):
        sys.exit('sound.wav.json has no clock: record with rtcaudio.py')
    epoch = rec.meta['epoch']
    first, last = rec.meta['packets'][0][1], rec.meta['packets'][-1][1]
    events = []
    with open(os.path.join(A.run, 'game.log'), errors='replace') as f:
        for line in f:
            m = LINE.search(line)
            if not m:
                continue
            y, mo, d, h, mi, s, ms = (int(v) for v in m.groups()[:7])
            wall = calendar.timegm((y, mo, d, h, mi, s)) + ms / 1000.0 - epoch
            events.append({'wall': wall, 'file': m.group(8), 'sound': m.group(9), 'category': m.group(10), 'volume': float(m.group(11)),
                           'mix': float(m.group(12)), 'pitch': float(m.group(13)), '3d': bool(m.group(14)), 'loop': bool(m.group(15))})
    if not events:
        sys.exit('no "LogMIAudioHost: Verbose: play" line in game.log: start the Development game with -LogCmds="LogMIAudioHost Verbose"')
    heard = [e for e in events if first + 0.2 <= e['wall'] <= last - 1.0]
    print(f"{len(events)} sounds started by the game ({len(events) - len(heard)} of them before the viewer listened or in its last second); "
          f"the recording is {rec.seconds:.1f} s; the viewer's clock starts {epoch:.3f}")
    sources, per_file, rows = {}, {}, {}
    for e in heard:
        n = per_file.get(e['file'], 0)
        per_file[e['file']] = n + 1
        row = rows.setdefault(e['sound'], {'category': e['category'], 'started': 0, 'tested': 0, 'found': 0, 'x': [], 'score': [], 'gain': [], 'expect': [],
                                           'delay': [], 'files': set(), '3d': e['3d'], 'loop': e['loop'], 'missed': []})
        row['started'] += 1
        if n >= A.per:
            continue
        if e['file'] not in sources:
            try:
                sources[e['file']] = af.mono48(os.path.join(A.audio, e['file']))
            except (OSError, ValueError):
                sources[e['file']] = None
        src = sources[e['file']]
        if src is None:
            continue
        row['tested'] += 1
        # A long template for what plays at its own speed for long (music, beds, loops): a tune is not itself
        # backwards. A short one for the rest (a shot's body).
        chunk = min(len(src) / af.RATE, 2.0 if e['loop'] else 0.3)
        a, b = rec.media(e['wall'] - 0.15), rec.media(e['wall'] + 0.9)
        part = rec.cut(max(0.0, a - 0.05), b + chunk / max(0.25, e['pitch']) + 0.2)
        hits, top = af.find(part, src, [e['pitch']], chunk=chunk, min_x=A.min_x, max_n=1)
        if not hits:
            row['missed'].append(f"{e['file']} at {e['wall']:.1f} s ({top:.2f} x chance)")
            continue
        h = hits[0]
        row['found'] += 1
        row['files'].add(e['file'])
        row['x'].append(h['x'])
        row['score'].append(h['score'])
        row['gain'].append(h['gainDb'])
        row['expect'].append(20 * math.log10(max(1e-6, e['volume'] * e['mix'])))
        row['delay'].append((rec.arrival(h['seconds']) - e['wall']) * 1000.0)
    order = ['music', 'ambience', 'ui', 'gun', 'tail', 'near', 'world', 'voice']
    print('category | sound | started | found of looked at | x chance | score | gain dB (measured; the game\'s volume x mix) | ms from the log line to the packet | files matched')
    out = []
    for name, r in sorted(rows.items(), key=lambda kv: (order.index(kv[1]['category']) if kv[1]['category'] in order else 99, kv[0])):
        kind = r['category'] + (' 3D' if r['3d'] else '') + (' loop' if r['loop'] else '')
        if r['found']:
            print(f"{kind} | {name} | {r['started']} | {r['found']} of {r['tested']} | {median(r['x']):.1f} | {median(r['score']):.2f} | "
                  f"{median(r['gain']):+.1f}; {median(r['expect']):+.1f} | {median(r['delay']):.0f} ({min(r['delay']):.0f} to {max(r['delay']):.0f}) | {', '.join(sorted(r['files']))}")
        else:
            print(f"{kind} | {name} | {r['started']} | 0 of {r['tested']} | - | - | - | - | not found: {'; '.join(r['missed'][:3])}")
        out.append({'sound': name, 'category': r['category'], '3d': r['3d'], 'loop': r['loop'], 'started': r['started'], 'tested': r['tested'], 'found': r['found'],
                    'x': median(r['x']), 'score': median(r['score']), 'gainDb': median(r['gain']), 'expectDb': median(r['expect']),
                    'delayMs': median(r['delay']), 'files': sorted(r['files']), 'missed': r['missed']})
    tested = sum(r['tested'] for r in rows.values())
    found = sum(r['found'] for r in rows.values())
    all_delays = [d for r in rows.values() if not r['loop'] for d in r['delay']]
    print(f"{found} of {tested} starts looked at were found in the recording ({len(rows)} different sounds, {sum(1 for r in rows.values() if r['found'])} of them found at least once); "
          f"from the game's log line to the packet with the sample's start: middle {median(all_delays):.0f} ms, shortest {min(all_delays, default=float('nan')):.0f}, longest {max(all_delays, default=float('nan')):.0f}")
    if A.json:
        with open(A.json, 'w') as f:
            json.dump(out, f, indent=1)


if __name__ == '__main__':
    main()
