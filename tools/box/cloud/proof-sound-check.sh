#!/bin/bash
# What the viewer of a stream proof heard: proof-keys.txt or proof-pad.txt played by rtcaudio.py
# (lag-test.sh run <name> game=ship view=proof-keys.txt audio=1 join=3 probe=0.25 secs=100), the recording looked
# through with audio_find.py for the game's own samples.
#
#   proof-sound-check.sh <run folder> [<Content/Audio>]
#
# It prints: when each of the script's markers fell on the sound's own clock; the title music and the street bed
# wherever they are found in the whole recording (templates of two seconds from four places of each loop, so that a
# place of it falls into the few seconds a first-time player spends on the click card and the set-up screens: the
# finds before the marker "run" are the home screen's); the run's first voice line and its radio clicks; the gun
# after each fire input (a click, or the controller's trigger), with the delay from the input to the arrival of the
# packet that holds the sample's start; the level, the peak and the clipped samples of every part; the recorder's own
# summary line and the game's count of sounds. Run it after the queue, never beside a run: numpy takes every core.
RUN=${1:?the run folder}
T=$(dirname "$(readlink -f "$0")")
AUDIO=${2:-/project/ue/repo-gameplay/unreal/MurderInc/Content/Audio}
PY=${PY:-/opt/venv/bin/python3}
W=$RUN/sound.wav
JIT=0.955:1.045:0.0025          # most sounds: a pitch jitter of 3.5 %
[ -f "$W" ] && [ -f "$W.json" ] || { echo "no $W (the run needs audio=1)"; exit 1; }
lines() { grep -E 'FOUND|^part|^ +at |other samples|cannot|^no |^delay from|^action|no occurrence' | sed 's/^/   /'; }
find_all() { "$PY" "$T/audio_find.py" "$W" --audio "$AUDIO" "$@" 2>&1 | lines; }
find_part() { local part=$1; shift; echo "== $part"; "$PY" "$T/audio_find.py" "$W" --audio "$AUDIO" --part "$part" "$@" 2>&1 | lines; }
has() { grep -q "^say .* $1\$" "$RUN/markers.txt"; }

echo "== the script's markers on the sound's clock (seconds of the recording)"
"$PY" - "$W.json" > "$RUN/markers.txt" <<'EOF'
import bisect, json, sys
m = json.load(open(sys.argv[1]))
packets = m.get('packets') or []
times = [p[1] for p in packets]
for t, line in m['actions']:
    if line.startswith('say ') and packets:
        i = min(len(packets) - 1, bisect.bisect_left(times, t))
        print(f"{line} = {packets[i][0] / m['rate']:.2f} s")
EOF
sed 's/^/   /' "$RUN/markers.txt"; sed -i 's/ = .*//' "$RUN/markers.txt"

echo "== the title music and the street, in the whole recording (those before the marker 'run' are the click card's and the set-up screens')"
for at in 0 5 10 15; do
  find_all --rates 1 --chunk 2 --at "$at" --max 6 Web/stem_drums_01.wav Web/stem_hats_01.wav Web/stem_keys_01.wav
done
for at in 0 3 6 9; do
  find_all --rates 1 --chunk 2 --at "$at" --max 8 Web/bed_day_01.wav
done

# The run's first line and its radio clicks come with the run's intro: after the Briefing's button (proof-keys.txt:
# under "briefing"; proof-pad.txt: under "start-buttons", whose fifth press it is).
for p in briefing start-buttons; do
  has "$p" && find_part "$p" --rates 1 --chunk 0.5 Voice/rule/inc_01.wav Voice/rule/inc_02.wav Voice/rule/inc_03.wav Web/radio_in_01.wav Web/radio_out_01.wav
done
for p in home crew-by-keyboard loadout-by-mouse block-by-keyboard; do
  has "$p" && find_part "$p" --rates 0.98:1.02:0.0025 --chunk 0.1 Web/ui_click_01.wav
done
# The gun: every fire input of the part, and the delay to the arrival of its sound.
ACTION=click; grep -q '^pad ' "$(sed -n 's/^view=//p' "$RUN/info.txt")" 2>/dev/null && ACTION="pad axis 6 1"
has fire && find_part fire --rates $JIT Gen/chopper_close_01.wav Gen/chopper_close_02.wav Gen/chopper_close_03.wav \
  Web/chopper_shot_01.wav Web/chopper_shot_02.wav Web/chopper_shot_03.wav Web/chopper_shot_04.wav Gen/chopper_tail_01.wav Gen/chopper_tail_02.wav \
  --decoys 12 --action "$ACTION"
has walk && find_part walk --rates $JIT --chunk 0.15 Gen/step_asphalt_01.wav Gen/step_asphalt_02.wav Gen/step_asphalt_03.wav Gen/step_asphalt_04.wav \
  Gen/step_concrete_01.wav Gen/step_concrete_02.wav Gen/step_concrete_03.wav

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
if says and rows:
    v = level(rows[0]['arrived'], says[0][0])
    if v:
        print(f"   {'(before ' + says[0][1] + ')':18s} {v[0]:6.1f} dBFS  loudest half second {v[1]:6.1f}  peak {v[2]:6.1f}  clipped {v[3]}  silent {v[4]} ms")
for k, (t, name) in enumerate(says):
    end = says[k + 1][0] if k + 1 < len(says) else rows[-1]['arrived']
    v = level(t, end)
    if v:
        print(f"   {name:18s} {v[0]:6.1f} dBFS  loudest half second {v[1]:6.1f}  peak {v[2]:6.1f}  clipped {v[3]}  silent {v[4]} ms")
EOF
grep -a 'SOUND\|drop-out' "$RUN/view.log" | cut -c1-400
grep -a 'MICloudProbe' "$RUN/game.log" | tail -1 | grep -o 'snd[A-Za-z]*=[0-9]*' | tr '\n' ' '; echo
