#!/bin/bash
# What the viewer of sound-keys.txt heard, part by part: for every part the script marks ("say SND <name>") the samples
# the game should have played there are looked for in the recording (audio_find.py), at the speeds the game plays them.
#
#   sound-keys-check.sh <run folder of lag-test.sh ... view=sound-keys.txt audio=1> [<Content/Audio>]
#
# One line per sample: FOUND (how often, how far above chance, its level against the file) or NOT FOUND. Then the
# levels the mix check needs: the loudness of each part, and the music's level on the pause card before, after forty
# presses of Left on the Volume row (80 % to 40 %: it must fall by 6.0 dB) and after forty presses of Right.
# The Shipping game has no log, so this and the game's own count (sndPlayed, sndMissing in its probe lines) are the proof
# for it; the Development game's proof is sound_table.py, which knows from the log what was started when.
RUN=${1:?the run folder}
T=$(dirname "$(readlink -f "$0")")
AUDIO=${2:-/project/ue/repo-gameplay/unreal/MurderInc/Content/Audio}
PY=${PY:-/opt/venv/bin/python3}
W=$RUN/sound.wav
JIT=0.955:1.045:0.0025          # most sounds: a pitch jitter of 3.5 %
find_part() {  # <part> <options...> -- files...
  local part=$1; shift
  echo "== $part"
  "$PY" "$T/audio_find.py" "$W" --audio "$AUDIO" --part "$part" "$@" 2>&1 | grep -E 'FOUND|other samples|cannot|^no |^delay from|no occurrence' | sed 's/^/   /'
}
find_part card --rates 1 --chunk 2 Web/stem_drums_01.wav Web/stem_hats_01.wav Web/stem_crackle_01.wav Web/bed_day_01.wav
find_part home --rates 1 --chunk 2 Web/stem_drums_01.wav Web/stem_hats_01.wav Web/stem_crackle_01.wav Web/bed_day_01.wav
find_part menu-moves --rates 0.98:1.02:0.0025 --chunk 0.1 Web/ui_hover_01.wav Web/ui_click_01.wav
for p in hit-the-block next-crew next-loadout next-block briefing; do
  find_part $p --rates 0.98:1.02:0.0025 --chunk 0.1 Web/ui_click_01.wav Web/ui_hover_01.wav
done
# The run's first line and its radio clicks come with the run's intro, which the script passes under "briefing".
find_part briefing --rates 1 --chunk 0.5 Voice/rule/inc_01.wav Voice/rule/inc_02.wav Voice/rule/inc_03.wav Web/radio_in_01.wav Web/radio_out_01.wav
find_part selector --rates 1.54:1.66:0.004 --chunk 0.1 Gen/dry_fire_01.wav Gen/dry_fire_02.wav Web/dry_fire_01.wav Web/dry_fire_02.wav
find_part single-shots --rates $JIT Gen/chopper_close_01.wav Gen/chopper_close_02.wav Gen/chopper_close_03.wav Gen/chopper_mech_01.wav Gen/chopper_mech_02.wav \
  Gen/chopper_tail_01.wav Gen/chopper_tail_02.wav Web/chopper_shot_01.wav Web/chopper_shot_02.wav Web/chopper_shot_03.wav Web/chopper_shot_04.wav \
  Gen/brass_asphalt_01.wav Gen/brass_asphalt_02.wav Gen/brass_asphalt_03.wav Gen/brass_concrete_01.wav Gen/brass_concrete_02.wav Gen/brass_concrete_03.wav \
  --decoys 12 --action click
find_part burst --rates $JIT Gen/chopper_close_01.wav Gen/chopper_close_02.wav Gen/chopper_close_03.wav --action "down 0"
find_part reload --rates $JIT Web/cloth_01.wav Web/cloth_02.wav Gen/rifle_magout_01.wav Gen/rifle_magin_01.wav Gen/rifle_bolt_01.wav \
  Web/rifle_magout_01.wav Web/rifle_magin_01.wav Web/rifle_bolt_01.wav --action "key 82"
find_part empty --rates $JIT Gen/chopper_close_01.wav Gen/chopper_close_02.wav Gen/chopper_close_03.wav
find_part dry --rates $JIT --chunk 0.1 Gen/dry_fire_01.wav Gen/dry_fire_02.wav Web/dry_fire_01.wav Web/dry_fire_02.wav --action click
find_part nine --rates $JIT Gen/nine_close_01.wav Gen/nine_close_02.wav Gen/nine_close_03.wav Gen/nine_mech_01.wav Gen/nine_mech_02.wav \
  Gen/nine_tail_01.wav Gen/nine_tail_02.wav Web/nine_shot_01.wav Web/nine_shot_02.wav --action click
find_part nine --rates 1.10:1.23:0.004 Web/holster_01.wav Web/draw_01.wav
find_part nine-reload --rates $JIT Gen/pistol_magout_01.wav Gen/pistol_magin_01.wav Gen/pistol_slide_01.wav Web/pistol_magout_01.wav Web/pistol_magin_01.wav Web/pistol_slide_01.wav
find_part chopper-again --rates $JIT Web/holster_01.wav Web/draw_01.wav
find_part melee --rates 1.05:1.15:0.004 Web/whoosh_01.wav --action "key 70"
find_part walk --rates $JIT --chunk 0.15 Gen/step_asphalt_01.wav Gen/step_asphalt_02.wav Gen/step_asphalt_03.wav Gen/step_asphalt_04.wav \
  Gen/step_concrete_01.wav Gen/step_concrete_02.wav Gen/step_concrete_03.wav Web/step_asphalt_01.wav Web/step_asphalt_02.wav Web/step_concrete_01.wav Web/step_concrete_02.wav
find_part sprint --rates 0.82:1.10:0.004 --chunk 0.15 Gen/step_asphalt_run_01.wav Gen/step_asphalt_run_02.wav Gen/step_asphalt_run_03.wav \
  Gen/step_concrete_run_01.wav Gen/step_concrete_run_02.wav Web/step_asphalt_run_01.wav Web/step_asphalt_run_02.wav Web/step_concrete_run_01.wav
find_part jump --rates $JIT Web/jump_01.wav Web/land_01.wav --action "key 32"
find_part pause --rates 1 --chunk 2 Web/stem_drums_01.wav Web/stem_hats_01.wav Web/stem_crackle_01.wav Web/bed_day_01.wav
find_part pause-menu --rates 0.98:1.02:0.0025 --chunk 0.1 Web/ui_hover_01.wav Web/ui_click_01.wav
find_part resume --rates 1 --chunk 2 Web/stem_drums_01.wav Web/bed_day_01.wav
echo "== levels (dBFS RMS of each part, its loudest half second, its peak)"
"$PY" - "$W.json" <<'EOF'
import json, math, sys
m = json.load(open(sys.argv[1]))
says = [(t, l.split()[-1]) for t, l in m['actions'] if l.startswith('say ')]
rows = [r for r in m['rows'] if r['arrived'] is not None]
def level(a, b):
    xs = [r for r in rows if a <= r['arrived'] < b]
    if not xs:
        return None
    mean = 10 * math.log10(sum(10 ** (r['rms'] / 10) for r in xs) / len(xs))
    return mean, max(r['rms'] for r in xs), max(r['peak'] for r in xs), sum(r['clipped'] for r in xs), sum(r['silentMs'] for r in xs)
out = {}
for k, (t, name) in enumerate(says):
    end = says[k + 1][0] if k + 1 < len(says) else rows[-1]['arrived']
    v = level(t, end)
    if v:
        out[name] = v
        print(f"   {name:16s} {v[0]:6.1f} dBFS  loudest half second {v[1]:6.1f}  peak {v[2]:6.1f}  clipped {v[3]}  silent {v[4]} ms")
# The Volume row: the last two seconds of each of the three parts (the presses themselves click).
def tail(name):
    for k, (t, n) in enumerate(says):
        if n == name:
            end = says[k + 1][0]
            return level(end - 2.5, end - 0.5)
before, down, up = tail('pause-menu'), tail('volume-down'), tail('volume-up')
if before and down and up:
    print(f"   the music on the pause card: {before[0]:.1f} dBFS before, {down[0]:.1f} after Left x 40 ({down[0] - before[0]:+.1f} dB; 80 % to 40 % is -6.0), {up[0]:.1f} after Right x 40 ({up[0] - before[0]:+.1f} dB)")
EOF
grep -a 'SOUND\|drop-out' "$RUN/view.log" | cut -c1-400
grep -a 'MICloudProbe' "$RUN/game.log" | tail -1 | grep -o 'snd[A-Za-z]*=[0-9]*' | tr '\n' ' '; echo
