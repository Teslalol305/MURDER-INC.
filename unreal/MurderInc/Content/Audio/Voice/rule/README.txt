PLACEHOLDER VOICE TAKES - NOT THE CHARACTER'S VOICE

Every WAV in this folder is, for now, a stand-in: text-to-speech on built-in stock preset voices (seed_audio),
the prompt being only the line's own text (tools/audio/voice_plan.json). No voice was cloned or imitated and no
released recording was sampled. voice.json marks each take "placeholder": true; the game logs
"voice: N of M takes are placeholders" when a world starts, and development builds draw a small
"placeholder voice" tag under the subtitle.

The real recordings replace these files one for one, under the same names (murda_01.wav, ...), with no code
change: python3 tools/audio/voice_ingest.py <the recordings> converts, trims and levels them and sets
"placeholder": false. The recording brief (with a phone or in a studio) is docs/unreal/AUDIO.md section 5.
