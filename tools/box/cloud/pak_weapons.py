# Does the package hold every gun, magazine and part mesh the game's data names? The guns of weapons round 4 (the
# CHOPPER and NINE with their own art, the SHORTY, the STRETCH, the RATTLER, their magazines, the brass and the twelve
# parts of the kit) are generated content: tools/box/fp/mi_guns_r4.py imports them on the box, nothing of them is in
# git. A package made from a copy that never ran the import has none of them, the cook has nothing to cook, the game
# finds no mesh, and nothing says so (as with the sounds of versions 1 to 3a: pak_sounds.py).
#
#   python3 pak_weapons.py <packaged folder: the one with MurderInc.sh and Manifest_UFSFiles_Linux.txt>
#   python3 pak_weapons.py --names <Content/Data folder>      only list the object paths the data names
#
# It reads the data the packaged game itself reads (<folder>/MurderInc/Content/Data/*.json), collects every object
# path it names ("/Game/<folder>/<name>.<name>"), and looks each one up in the pak's own list (an object path
# /Game/X/Y.Y is the cooked package MurderInc/Content/X/Y.uasset or .umap). Every path under /Game/Weapons must be
# there; a path under another folder that is not there is listed as a note (those are the level, the characters and
# the pack's content, which earlier packages carried; the weapons are what this guard is for). Prints one line and
# exits 0 when every weapons path is there, 1 when one is missing.
import json
import os
import re
import sys

OBJECT_PATH = re.compile(r'^/Game/[A-Za-z0-9_/]+\.[A-Za-z0-9_]+$')
REQUIRED = '/Game/Weapons/'


def names(data):
    found = {}

    def walk(node, source):
        if isinstance(node, dict):
            for v in node.values():
                walk(v, source)
        elif isinstance(node, list):
            for v in node:
                walk(v, source)
        elif isinstance(node, str) and OBJECT_PATH.match(node):
            found.setdefault(node, set()).add(source)

    for name in sorted(os.listdir(data)):
        if name.endswith('.json'):
            with open(os.path.join(data, name), encoding='utf-8') as f:
                walk(json.load(f), name)
    return found


def package_file(path):
    package = path.split('.', 1)[0]                 # /Game/Weapons/Shorty/SK_Shorty
    return 'MurderInc/Content/' + package[len('/Game/'):]


def main():
    if len(sys.argv) == 3 and sys.argv[1] == '--names':
        for p, src in sorted(names(sys.argv[2]).items()):
            print(f'{p}\t{",".join(sorted(src))}')
        return 0
    if len(sys.argv) != 2:
        print(__doc__ or 'usage: pak_weapons.py <packaged folder>')
        return 2
    folder = sys.argv[1]
    try:
        wanted = names(os.path.join(folder, 'MurderInc', 'Content', 'Data'))
        with open(os.path.join(folder, 'Manifest_UFSFiles_Linux.txt'), encoding='utf-8', errors='replace') as f:
            listed = {line.split('\t', 1)[0].strip() for line in f}
    except (OSError, ValueError) as e:
        print(f'WEAPONS UNKNOWN: {folder} cannot be checked ({e})')
        return 1

    def there(p):
        stem = package_file(p)
        return stem + '.uasset' in listed or stem + '.umap' in listed

    weapons = sorted(p for p in wanted if p.startswith(REQUIRED))
    missing = [p for p in weapons if not there(p)]
    others = sorted(p for p in wanted if not p.startswith(REQUIRED) and not there(p))
    cooked = sum(1 for p in listed if p.startswith('MurderInc/Content/Weapons/') and p.endswith('.uasset'))
    note = ''
    if others:
        note = (f' Note, not weapons: {len(others)} other object path(s) the data names are not in the pak list either: '
                f'{", ".join(others[:6])}{" ..." if len(others) > 6 else ""}.')
    if missing:
        print(f'WEAPONS MISSING: the game\'s data names {len(weapons)} assets under /Game/Weapons and the pak list of {folder} '
              f'holds {len(weapons) - len(missing)} of them ({cooked} packages under MurderInc/Content/Weapons/ in all); missing: '
              f'{", ".join(m.rsplit("/", 1)[1].split(".")[0] for m in missing[:10])}{" ..." if len(missing) > 10 else ""}. '
              'The game would find no mesh for them. Run the weapons import (tools/box/fp/mi_guns_r4.py: package-cloud.sh '
              'weapons) in the release copy, then package again.' + note)
        return 1
    print(f'WEAPONS OK: all {len(weapons)} assets under /Game/Weapons the game\'s data names are in the pak list of {folder} '
          f'({cooked} packages under MurderInc/Content/Weapons/).' + note)
    return 0


if __name__ == '__main__':
    sys.exit(main())
