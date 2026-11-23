PLACEHOLDER SOUND EFFECTS - GENERATED, NOT RECORDED

Every WAV in this folder except bleep_1k.wav is generated (text-to-audio, mirelo_text_to_audio; the prompts are
tools/audio/sfx_plan.json) and cut and levelled by tools/audio/sfx_process.py: one loudness per variant set,
matched to the web sound it plays over. In Content/Data/audio.json every replacement layer that plays these
files says "placeholder": true (MurderInc.Audio.EventTable counts them).

Recorded or licensed material replaces them one for one under the same names; set the layer's "placeholder" to
false, then run tools/box/audio-import.sh. MurderInc.Audio.GenFiles checks each variant set: no variant under half
the median length of its set, every variant's loudness within 3 dB of the set's. docs/unreal/AUDIO.md section 6.
