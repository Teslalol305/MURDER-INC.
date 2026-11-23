"""Box, headless: import the packed Goons (goons-pack.sh unpack) into the chars project.
    bash cmdlet.sh /project/ue/chars/scripts/goons_setup.py goons_setup     (poll the log for MI-DONE)"""
import json
import sys

sys.path.insert(0, "/project/ue/chars/scripts")
import unreal  # noqa: E402
import mi_chars  # noqa: E402

rep = mi_chars.setup_goons()
print("MI-REPORT " + json.dumps(rep)[:4000])
print("MI-DONE")
