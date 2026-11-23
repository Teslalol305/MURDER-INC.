"""Bring real voice recordings into the game (docs/unreal/AUDIO.md section 5): any format ffmpeg reads (a phone's
.m4a, .wav, .aiff, .flac, .mp3 ...) becomes a 48 kHz 24-bit mono WAV under Content/Audio/Voice/<character>/,
trimmed to the line with 100 ms before and 300 ms after it, loudness-normalised to -18 LUFS integrated with peaks
under -1 dBFS, and the take in Content/Data/voice.json is marked placeholder: false. A report gives each take's
length, its longest silence inside and the checks of MurderInc.Audio.VoiceData (under 2.5 s, the crowd chant under
2.2 s, no silence over 0.5 s inside).

File names say where a recording goes:
  murda_02.m4a              replaces the take murda_02.wav of the line murda
  murda_04_shout.m4a        a NEW take murda_04.wav of the line murda, intensity shout (shout, spoken or breath)
  name_clean_02.wav         the clean-language take 2 of the line name
Anything else is reported and skipped. Nothing is overwritten with --dry-run.

Bleep marks (only needed when voice.json says clean mode "bleep"): --bleep name_01=0.62:0.98 gives the profane
word's start and end in seconds of the ORIGINAL file; the script moves them with the trim.

Usage: python3 tools/audio/voice_ingest.py <file or folder> [...] [--character rule] [--dry-run] [--bleep take=a:b ...]
Then: commit the WAVs and voice.json, and on the box run tools/box/audio-import.sh (AUDIO.md section 7).
"""
import argparse
import json
import os
import re
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wavtools as wt  # noqa: E402

RATE = 48000
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
VOICE_JSON = os.path.join(ROOT, 'unreal/MurderInc/Content/Data/voice.json')
AUDIO = ('.m4a', '.aac', '.mp4', '.wav', '.wave', '.aif', '.aiff', '.flac', '.mp3', '.ogg', '.opus', '.caf', '.3gp', '.amr', '.webm')
NAME = re.compile(r'^(?P<take>(?P<prefix>[a-z]+(?:_[a-z]+)*)_(?P<n>\d{2}))(?:_(?P<intensity>shout|spoken|breath))?$')


def decode(path):
    out = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '1', '-ar', str(RATE), '-'], capture_output=True)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.decode(errors='replace').strip()[:300])
    return np.frombuffer(out.stdout, dtype='<f4').astype(np.float64)


def frames_db(x):
    hop = RATE // 100
    n = len(x) // hop
    e = np.array([np.mean(x[i * hop:(i + 1) * hop] ** 2) for i in range(n)]) + 1e-20
    return 10 * np.log10(e)


def trim(x, pre=0.10, post=0.30, rel_db=-40.0):
    """The line with `pre` s before its first sound and `post` s after its last (10 ms frames within rel_db of the
    loudest); short fades at both ends. Returns (samples, first sample kept)."""
    db = frames_db(x)
    on = np.where(db > db.max() + rel_db)[0]
    if len(on) == 0:
        return x, 0
    a = max(0, on[0] * (RATE // 100) - int(pre * RATE))
    b = min(len(x), (on[-1] + 1) * (RATE // 100) + int(post * RATE))
    y = x[a:b].copy()
    f = int(0.005 * RATE)
    y[:f] *= np.linspace(0, 1, f)
    g = int(0.05 * RATE)
    y[-g:] *= np.linspace(1, 0, g)
    return y, a


def inner_gap(x, rel_db=-40.0):
    db = frames_db(x)
    on = db > db.max() + rel_db
    idx = np.where(on)[0]
    if len(idx) == 0:
        return 0.0
    run = best = 0
    for v in on[idx[0]:idx[-1] + 1]:
        run = 0 if v else run + 1
        best = max(best, run)
    return best * 0.01


def where(voice, character, prefix):
    """(line id, 'takes' or 'clean') for a take prefix such as murda or name_clean."""
    lines = voice['characters'][character]['lines']
    if prefix in lines:
        return prefix, 'takes'
    if prefix.endswith('_clean') and prefix[:-6] in lines:
        return prefix[:-6], 'clean'
    return None, None


def mark(text, file, intensity, prefix, bleep):
    """Set placeholder false on the take `file` in voice.json's text (or add it after its last sibling), keeping
    the file's own formatting. Returns the new text and what was done."""
    pat = re.compile(r'\{ "file": "%s"[^}]*\}' % re.escape(file))
    m = pat.search(text)
    if m:
        entry = m.group(0)
        new = entry.replace('"placeholder": true', '"placeholder": false')
        if intensity:
            new = re.sub(r'"intensity": "[a-z]+"', '"intensity": "%s"' % intensity, new)
        if bleep:
            new = re.sub(r'"bleep": \[[^\]]*\]', '"bleep": [%.3f, %.3f]' % bleep, new) if '"bleep"' in new else new[:-2] + ', "bleep": [%.3f, %.3f] }' % bleep
        return text[:m.start()] + new + text[m.end():], 'replaced'
    sib = list(re.finditer(r'(\n(\s*))\{ "file": "%s_\d{2}\.wav"[^}]*\}' % re.escape(prefix), text))
    if not sib:
        return text, None
    last = sib[-1]
    entry = '{ "file": "%s", "intensity": "%s", "placeholder": false%s }' % (
        file, intensity or 'spoken', ', "bleep": [%.3f, %.3f]' % bleep if bleep else '')
    return text[:last.end()] + ',' + last.group(1) + entry + text[last.end():], 'added'


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('inputs', nargs='+')
    ap.add_argument('--character', default='rule')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--bleep', action='append', default=[], help='take=start:end in seconds of the original file')
    a = ap.parse_args()
    bleeps = {}
    for b in a.bleep:
        k, _, v = b.partition('=')
        s0, _, s1 = v.partition(':')
        bleeps[k] = (float(s0), float(s1))
    files = []
    for p in a.inputs:
        if os.path.isdir(p):
            files += [os.path.join(p, f) for f in sorted(os.listdir(p)) if f.lower().endswith(AUDIO)]
        else:
            files.append(p)
    text = open(VOICE_JSON, encoding='utf-8').read()
    voice = json.loads(text)
    out_dir = os.path.join(ROOT, 'unreal/MurderInc/Content/Audio/Voice', a.character)
    os.makedirs(out_dir, exist_ok=True)
    bad = 0
    for path in files:
        stem = os.path.splitext(os.path.basename(path))[0].lower().replace('-', '_').replace(' ', '_')
        m = NAME.match(stem)
        if not m:
            print(f'SKIP {path}: the name must be <line>_<NN>[_shout|_spoken|_breath], e.g. murda_02.m4a')
            bad += 1
            continue
        take, prefix, intensity = m.group('take'), m.group('prefix'), m.group('intensity')
        line, _ = where(voice, a.character, prefix)
        if not line:
            print(f'SKIP {path}: no line "{prefix}" for {a.character} in voice.json')
            bad += 1
            continue
        try:
            x = decode(path)
        except RuntimeError as e:
            print(f'SKIP {path}: ffmpeg cannot read it ({e})')
            bad += 1
            continue
        y, start = trim(x)
        y = wt.normalise(y, RATE, target=-18.0, ceiling=-1.0)
        secs, gap = len(y) / RATE, inner_gap(y)
        limit = 2.2 if line == 'rule_chant' else 2.5
        notes = []
        if secs > limit:
            notes.append(f'LONGER than {limit} s: the game check fails; cut the line tighter or record it quicker')
        if gap > 0.5:
            notes.append(f'{gap:.2f} s of silence inside: over 0.5 s, the game check fails')
        loud = wt.lufs(y, RATE)
        peak = 20 * np.log10(np.max(np.abs(y)) + 1e-12)
        if loud < -21.0:
            notes.append('quiet even at the -1 dBFS ceiling: a peak (pop, knock) is holding it down, try another take')
        bleep = None
        if take in bleeps:
            s0, s1 = bleeps[take]
            bleep = (max(0.0, s0 - start / RATE), max(0.0, s1 - start / RATE))
        file = take + '.wav'
        what = 'dry run'
        if not a.dry_run:
            wt.write24(os.path.join(out_dir, file), y, RATE)
            text, what = mark(text, file, intensity, prefix, bleep)
            what = what or 'written, but NOT in voice.json (add the take by hand)'
        print(f'{"OK  " if not notes else "WARN"} {file:20s} {secs:5.2f} s  inner gap {gap:4.2f} s  {loud:6.1f} LUFS  peak {peak:5.1f} dBFS  {what}'
              + ''.join(f'\n       {n}' for n in notes))
        bad += 1 if notes else 0
    if not a.dry_run:
        json.loads(text)
        open(VOICE_JSON, 'w', encoding='utf-8').write(text)
    print(f'{len(files)} file(s), {bad} with something to look at. Next: commit, then tools/box/audio-import.sh on the box.')


if __name__ == '__main__':
    main()
