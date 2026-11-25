"""Imports every WAV under Content/Audio (Web, Gen, Voice) as a Sound Wave next to it: Content/Audio/Web/x_01.wav
becomes /Game/Audio/Web/x_01 (docs/unreal/AUDIO.md section 4). Loops (audio_sounds.json loop flag, and the Gen files
the replacement table uses as loops) get bLooping. Re-running replaces what is there, so a real recording dropped in
under a placeholder's file name takes its place with no code or data change.

Run headless on the box: tools/box/audio-import.sh (UnrealEditor-Cmd -run=pythonscript).
Writes <project>/Saved/AudioImport/status.txt: one line per file, then AUDIO-IMPORT-DONE imported=N failed=N.
"""
import json
import os

import unreal

PROJECT = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
CONTENT = os.path.join(PROJECT, 'Content')
AUDIO = os.path.join(CONTENT, 'Audio')
STATUS_DIR = os.path.join(PROJECT, 'Saved', 'AudioImport')
GEN_LOOPS = ('rotor_loop', 'train_pass', 'roomtone_day')
# A loop of the music or the street keeps its voice and its place in time even at no volume (play when silent): the
# engine otherwise virtualises a silent loop and starts it from its first sample when it comes back, which put the
# strings and the bell off the beat. The game sets the same at run time (UMIAudioSubsystem::ApplyVoicePolicy), so a
# wave imported before this still keeps time; the flag on the asset says it where an editor looks.
KEEP_BUSES = ('music', 'amb')
GEN_KEEP = ('roomtone_day',)


def loops():
    """(every looping sound, those of them that keep their voice and their place in time)."""
    names, keep = set(), set()
    try:
        with open(os.path.join(CONTENT, 'Data', 'audio_sounds.json'), encoding='utf-8') as f:
            for name, d in json.load(f)['sounds'].items():
                if d.get('loop'):
                    names.add(name)
                    if d.get('bus') in KEEP_BUSES:
                        keep.add(name)
    except (OSError, ValueError, KeyError):
        pass
    return names, keep


def main():
    os.makedirs(STATUS_DIR, exist_ok=True)
    looping, keeping = loops()
    tasks = []
    for root, _, files in os.walk(AUDIO):
        for f in sorted(files):
            if not f.lower().endswith('.wav') or f.startswith('IR_'):
                continue
            rel = os.path.relpath(root, CONTENT).replace(os.sep, '/')
            t = unreal.AssetImportTask()
            t.filename = os.path.join(root, f)
            t.destination_path = '/Game/' + rel
            t.destination_name = os.path.splitext(f)[0]
            t.automated = True
            t.replace_existing = True
            t.save = True
            tasks.append(t)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    ok = failed = 0
    lines = []
    for t in tasks:
        path = f'{t.destination_path}/{t.destination_name}'
        asset = unreal.load_asset(path)
        if not asset:
            failed += 1
            lines.append(f'FAILED {path}')
            continue
        stem = t.destination_name
        base = stem.rsplit('_', 1)[0]
        if base in looping or stem.startswith(GEN_LOOPS):
            asset.set_editor_property('looping', True)
            if base in keeping or stem.startswith(GEN_KEEP):
                try:
                    asset.set_editor_property('virtualization_mode', unreal.VirtualizationMode.PLAY_WHEN_SILENT)
                except Exception as e:  # the game sets it at run time too: an editor without the property is not a failed import
                    unreal.log_warning(f'virtualization_mode not set on {path}: {e}')
            unreal.EditorAssetLibrary.save_loaded_asset(asset)
        ok += 1
        lines.append(f'OK {path} {asset.get_editor_property("duration"):.3f}s')
    with open(os.path.join(STATUS_DIR, 'status.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + f'\nAUDIO-IMPORT-DONE imported={ok} failed={failed}\n')
    unreal.log(f'AUDIO-IMPORT-DONE imported={ok} failed={failed}')


main()
