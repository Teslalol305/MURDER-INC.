# Does the package hold every sound the game can play? Versions 1, 2 and 3a of the cloud package held none: the Sound
# Wave assets had never been imported in the clone the package is made from, the cook had nothing to cook, the game
# skips a sound without its asset, and nothing said so (docs/unreal/PREFLIGHT.md V3-14).
#
#   python3 pak_sounds.py <packaged folder: the one with MurderInc.sh and Manifest_UFSFiles_Linux.txt>
#                         [--cooked <the cook's output: .../Saved/Cooked/Linux/MurderInc>] [--source <the Content folder cooked>]
#   python3 pak_sounds.py --names <Content/Data folder>      only list the Sound Waves the data names
#
# It reads the data the packaged game itself reads (<folder>/MurderInc/Content/Data/audio_sounds.json, audio.json,
# voice.json), works out every Sound Wave that data can ask for the way the game does (Audio/MIAudioData.cpp: every
# variant of every web sound except the two reverb responses, every file of every replacement layer, every take of
# every voice line of every character, the bleep tone; a file X.wav is the asset /Game/Audio/X), and looks each one
# up in the pak's own list: all three parts of a Sound Wave (.uasset, .uexp and .ubulk, which holds the audio itself:
# chopper_shot_01 is 814 bytes of .uasset, 130 of .uexp and 3,809 of .ubulk), not the name alone. A wave whose audio
# failed to encode (the cook runs with -IgnoreCookErrors) is "in the pak" by name and silent: with --cooked the cook's
# own output is looked at as well, and every named wave must have a .ubulk of more than 100 bytes there (the smallest
# real one is 415: ui_hover_01) and be at least as new as the asset it was cooked from (--source: an older cooked file
# is yesterday's recording: "package Shipping" used to skip the cook when any cook existed). Prints one line and exits 0
# when all is well, 1 when something is missing or empty.
import json
import os
import sys


def names(data):
    def load(name):
        with open(os.path.join(data, name), encoding='utf-8') as f:
            return json.load(f)

    files = set()
    for name, d in load('audio_sounds.json')['sounds'].items():
        if d.get('bus') == 'ir':
            continue
        for k in range(int(d.get('variants', 1))):
            files.add(f'Web/{name}_{k + 1:02d}.wav')
    for entry in load('audio.json').get('replace', {}).values():
        if isinstance(entry, dict):
            for layer in entry.get('layers', []):
                files.update(layer.get('files', []))
    for who, c in load('voice.json').get('characters', {}).items():
        for line in c.get('lines', {}).values():
            takes = list(line.get('takes', [])) + list((line.get('clean') or {}).get('takes', []))
            files.update(f"Voice/{who}/{t['file']}" for t in takes)
    files.add('Gen/bleep_1k.wav')
    return sorted(files)


PARTS = ('.uasset', '.uexp', '.ubulk')
MIN_BULK = 100   # bytes: a Sound Wave's audio in the cook's output (the smallest real one: 415)


def main():
    argv = sys.argv[1:]
    if len(argv) == 2 and argv[0] == '--names':
        print('\n'.join(names(argv[1])))
        return 0
    cooked = source = None
    for flag in ('--cooked', '--source'):
        if flag in argv:
            i = argv.index(flag)
            if i + 1 >= len(argv):
                print(__doc__ or 'usage: pak_sounds.py <packaged folder>')
                return 2
            if flag == '--cooked':
                cooked = argv[i + 1]
            else:
                source = argv[i + 1]
            del argv[i:i + 2]
    if len(argv) != 1:
        print(__doc__ or 'usage: pak_sounds.py <packaged folder>')
        return 2
    folder = argv[0]
    try:
        wanted = names(os.path.join(folder, 'MurderInc', 'Content', 'Data'))
        with open(os.path.join(folder, 'Manifest_UFSFiles_Linux.txt'), encoding='utf-8', errors='replace') as f:
            listed = {line.split('\t', 1)[0].strip() for line in f}
    except (OSError, ValueError, KeyError) as e:
        print(f'SOUNDS UNKNOWN: {folder} cannot be checked ({e})')
        return 1
    under = sum(1 for p in listed if p.startswith('MurderInc/Content/Audio/') and p.endswith('.uasset'))
    # By name: every wave has all three parts in the pak list.
    missing = [w for w in wanted if f"MurderInc/Content/Audio/{w[:-4]}.uasset" not in listed]
    partial = [f"{w[:-4]} (no {', '.join(e for e in PARTS if f'MurderInc/Content/Audio/{w[:-4]}{e}' not in listed)})"
               for w in wanted if w not in missing and any(f'MurderInc/Content/Audio/{w[:-4]}{e}' not in listed for e in PARTS)]
    if missing or partial:
        why = []
        if missing:
            why.append(f"{len(missing)} are not in the pak list at all ({', '.join(missing[:8])}{' ...' if len(missing) > 8 else ''})")
        if partial:
            why.append(f"{len(partial)} lack a part ({', '.join(partial[:6])}{' ...' if len(partial) > 6 else ''}): without its .ubulk a wave has no audio")
        print(f'SOUNDS MISSING: the game\'s data names {len(wanted)} Sound Waves and the pak list of {folder} holds {len(wanted) - len(missing) - len(partial)} of them whole '
              f'({under} Sound Waves under MurderInc/Content/Audio/ in all); {"; ".join(why)}. '
              'The game would play nothing for them. Run tools/box/audio-import.sh in the gameplay clone, then package again.')
        return 1
    note = ''
    if cooked:
        # The cook's own output: the audio itself must be there, and not older than the asset it was cooked from.
        empty, old, absent = [], [], []
        for w in wanted:
            rel = w[:-4]
            bulk = os.path.join(cooked, 'Content', 'Audio', rel + '.ubulk')
            asset = os.path.join(cooked, 'Content', 'Audio', rel + '.uasset')
            try:
                if os.path.getsize(bulk) <= MIN_BULK:
                    empty.append(f'{rel} ({os.path.getsize(bulk)} bytes)')
            except OSError:
                absent.append(rel)
                continue
            if source:
                try:
                    if os.path.getmtime(asset) + 1 < os.path.getmtime(os.path.join(source, 'Audio', rel + '.uasset')):
                        old.append(rel)
                except OSError:
                    pass
        if absent or empty or old:
            bad = []
            if absent:
                bad.append(f"{len(absent)} have no .ubulk in the cook's output ({', '.join(absent[:6])}{' ...' if len(absent) > 6 else ''})")
            if empty:
                bad.append(f"{len(empty)} have a .ubulk of {MIN_BULK} bytes or less, a wave that holds no audio ({', '.join(empty[:6])}{' ...' if len(empty) > 6 else ''})")
            if old:
                bad.append(f"{len(old)} were cooked from an older asset than the one in the release copy: the cook is old ({', '.join(old[:6])}{' ...' if len(old) > 6 else ''}); cook again")
            print(f'SOUNDS EMPTY: the cook\'s output {cooked} is not what the game needs: {"; ".join(bad)}.')
            return 1
        note = f'; the cook\'s output holds every one with audio (.ubulk over {MIN_BULK} bytes' + (', none older than its asset)' if source else ')')
    print(f'SOUNDS OK: all {len(wanted)} Sound Waves the game\'s data names are in the pak list of {folder} with .uasset, .uexp and .ubulk ({under} under MurderInc/Content/Audio/){note}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
