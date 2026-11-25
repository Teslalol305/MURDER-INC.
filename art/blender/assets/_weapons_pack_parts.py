"""Round 4, lane 2: the archives of the parts kit and of the two patched guns, in the layout of fp-guns.tar (`glb/*.glb`,
`textures/<Set>/T_<Set>_{BC,N,ORM[,E,A]}.png`), importable the same way (`tools/box/fp/fp-art.sh unpack`, `import-chars.sh`):

    python art/blender/assets/_weapons_pack_parts.py            # art/out/fp-weapons-parts.tar, art/out/fp-weapons-mounts.tar

fp-weapons-parts.tar    the 15 SM_Part_* files (nine hardware parts, three magazines, three top rounds) with their
                        `.sockets.json`, the sets Weapon_Parts (BC N ORM E) and Weapon_PartsMags (BC N ORM), and
                        `weapons_parts_contract.json` (every socket in the part's frame, metres and Unreal centimetres, the
                        slots, the sizes: a static mesh's sockets are written from it at import, like the pack parts').
fp-weapons-mounts.tar   SK_Chopper.glb and SK_Nine.glb with the new sockets and the Booster / FrontSight bones (+ their
                        verify files) with the sets they read, and the two standard magazines with theirs (the guns' sets are
                        large: 4K x 3 for the CHOPPER).
Each tar stays under the storage's limit (240 MB); `weapons_r4_parts.json` inside is the contract. Nothing from the pack is
touched, nothing here is committed (art/out is git-ignored)."""
import json
import os
import shutil
import sys
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
OUT = os.path.join(REPO, "art", "out")
STAGE = os.path.join(OUT, "fp-weapons-stage")
CONTRACT = os.path.join(HERE, "weapons_parts_contract.json")
LIMIT = 240e6


def stage_set(name):
    d = os.path.join(OUT, "textures", name)
    t = os.path.join(STAGE, "textures", name)
    os.makedirs(t, exist_ok=True)
    for k in ("BC", "N", "ORM", "E", "A"):
        f = os.path.join(d, "T_%s_%s.png" % (name, k))
        if os.path.exists(f):
            shutil.copy2(f, t)


def stage_glb(name, extra=()):
    os.makedirs(os.path.join(STAGE, "glb"), exist_ok=True)
    for ext in (".glb",) + tuple(extra):
        f = os.path.join(OUT, "glb", name + ext)
        if os.path.exists(f):
            shutil.copy2(f, os.path.join(STAGE, "glb"))


def tar_stage(path):
    with tarfile.open(path, "w") as tar:
        for root, _d, files in os.walk(STAGE):
            for f in sorted(files):
                full = os.path.join(root, f)
                tar.add(full, arcname=os.path.relpath(full, STAGE))
    return os.path.getsize(path)


def main():
    ct = json.load(open(CONTRACT))
    for kind in ("parts", "mounts"):
        shutil.rmtree(STAGE, ignore_errors=True)
        os.makedirs(STAGE)
        if kind == "parts":
            for pid, rec in ct["parts"].items():
                stage_glb(rec["mesh"], (".sockets.json",))
                if rec.get("top_round_mesh"):
                    stage_glb(rec["top_round_mesh"])
            for s in ("Weapon_Parts", "Weapon_PartsMags"):
                stage_set(s)
            shutil.copy2(CONTRACT, os.path.join(STAGE, "weapons_r4_parts.json"))
            path = os.path.join(OUT, "fp-weapons-parts.tar")
        else:
            for g in ("SK_Chopper", "SK_Nine"):
                stage_glb(g, (".glb.verify.json", ".patch.json"))
            for m in ("SM_Weapon_ChopperMagazine", "SM_Weapon_ChopperMagazine_TopRound", "SM_Weapon_NineMagazine", "SM_Weapon_NineMagazine_TopRound"):
                stage_glb(m)
            for s in ("Chopper", "Chopper_Furniture", "Chopper_Front", "Weapon_ChopperMagazine", "Nine", "Weapon_NineMagazine"):
                stage_set(s)
            shutil.copy2(CONTRACT, os.path.join(STAGE, "weapons_r4_parts.json"))
            path = os.path.join(OUT, "fp-weapons-mounts.tar")
        size = tar_stage(path)
        print("%s: %.1f MB (%s)" % (os.path.relpath(path, REPO), size / 1e6, "OK" if size <= LIMIT else "OVER THE 240 MB LIMIT: split it"))
    shutil.rmtree(STAGE, ignore_errors=True)


if __name__ == "__main__":
    main()
