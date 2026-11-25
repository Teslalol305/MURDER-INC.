# Does the package hold every sound the game can play? Versions 1, 2 and 3a of the cloud package held none: the Sound
# Wave assets had never been imported in the clone the package is made from, the cook had nothing to cook, the game
# skips a sound without its asset, and nothing said so (docs/unreal/PREFLIGHT.md V3-14).
#
#   python3 pak_sounds.py <packaged folder: the one with MurderInc.sh and Manifest_UFSFiles_Linux.txt>
#   python3 pak_sounds.py --names <Content/Data folder>      only list the Sound Waves the data names
#
# It reads the data the packaged game itself reads (<folder>/MurderInc/Content/Data/audio_sounds.json, audio.json,
# voice.json), works out every Sound Wave that data can ask for the way the game does (Audio/MIAudioData.cpp: every
# variant of every web sound except the two reverb responses, every file of every replacement layer, every take of
# every voice line of every character, the bleep tone; a file X.wav is the asset /Game/Audio/X), and looks each one
# up in the pak's own list. Prints one line and exits 0 when all are there, 1 when one is missing.
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


def main():
    if len(sys.argv) == 3 and sys.argv[1] == '--names':
        print('\n'.join(names(sys.argv[2])))
        return 0
    if len(sys.argv) != 2:
        print(__doc__ or 'usage: pak_sounds.py <packaged folder>')
        return 2
    folder = sys.argv[1]
    try:
        wanted = names(os.path.join(folder, 'MurderInc', 'Content', 'Data'))
        with open(os.path.join(folder, 'Manifest_UFSFiles_Linux.txt'), encoding='utf-8', errors='replace') as f:
            listed = {line.split('\t', 1)[0].strip() for line in f}
    except (OSError, ValueError, KeyError) as e:
        print(f'SOUNDS UNKNOWN: {folder} cannot be checked ({e})')
        return 1
    under = sum(1 for p in listed if p.startswith('MurderInc/Content/Audio/') and p.endswith('.uasset'))
    missing = [w for w in wanted if f"MurderInc/Content/Audio/{w[:-4]}.uasset" not in listed]
    if missing:
        print(f'SOUNDS MISSING: the game\'s data names {len(wanted)} Sound Waves and the pak list of {folder} holds {len(wanted) - len(missing)} of them '
              f'({under} Sound Waves under MurderInc/Content/Audio/ in all); missing: {", ".join(missing[:8])}{" ..." if len(missing) > 8 else ""}. '
              'The game would play nothing for them. Run tools/box/audio-import.sh in the gameplay clone, then package again.')
        return 1
    print(f'SOUNDS OK: all {len(wanted)} Sound Waves the game\'s data names are in the pak list of {folder} ({under} under MurderInc/Content/Audio/)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
