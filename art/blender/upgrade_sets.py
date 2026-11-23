"""Texture-density pass (docs/unreal/PROGRESS.md "Exact next step" 2): bring the sets that fall under about
1,024 px/m near the player up, and give the tinted paint slots their tile size in the manifest.

    venv/bin/python art/blender/upgrade_sets.py            # all three steps
    venv/bin/python art/blender/upgrade_sets.py manifest   # only the manifest step

1. Scanned sets: their 4K sources come from `python3 art/scans/fetch.py --res 4k --only <sets>` (art/scans/README.md):
   the convention files are replaced under the same set names and tile sizes, so nothing on the meshes changes.
   TS_Roof_ScanBitumen covers a 5.4 m tile, so even 4K gives only 758 px/m: it is fetched at 8K instead
   (`fetch.py --res 8k --only TS_Roof_ScanBitumen`, 1,517 px/m). Fetch the 4K list first and the 8K one after it.
2. Procedural sets (galvanised, road paint): re-baked at 2048 px over the same tile with the parameters recorded in
   their own set.json (mi.bake caches by parameters and resolution). A family that bakes them again with an explicit
   lower `res` (furniture: `res=1024`) would bring them back down: run this script after such a bake.
3. Manifest: every texture set entry is re-read from its files (density, resolution), and every material slot that
   names a set but carries no `tile_m` (the tinted slots MI_Steel_Paint*, MI_Steel_IronDark, MI_Block_Dado*, ...: their
   slot name does not spell the set they read, so mi.export could not look it up) gets the set's tile and density.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

SCANNED_8K = ["TS_Roof_ScanBitumen"]
SCANNED_4K = ["TS_Concrete_ScanFormed", "TS_Steel_ScanRust", "TS_Brick_ScanRedCommon",
              "TS_Sidewalk_ScanWorn", "TS_Asphalt_ScanWorn", "TS_Shutter_ScanGrey", "TS_Asphalt_ScanFresh",
              "TS_Wood_ScanPlankDark"]
PROCEDURAL_2K = ["TS_Galvanised_Aged", "TS_RoadPaint_White", "TS_RoadPaint_Yellow"]


def rebake(res=2048):
    import bpy  # noqa: F401
    from mi import bake, paths, scene
    scene.reset()
    for name in PROCEDURAL_2K:
        with open(os.path.join(paths.texture_set(name), "set.json")) as f:
            info = json.load(f)
        params = {k: (tuple(v) if isinstance(v, list) else v) for k, v in info.get("params", {}).items()}
        tile = info["tile_m"]
        bake.bake_tiling_set(name, info["surface"], tile if tile[0] != tile[1] else tile[0], res, 4, **params)


def patch_manifest():
    from mi import export, paths

    def upd(data):
        sets = data.setdefault("texture_sets", {})
        for name in list(sets) + SCANNED_8K + SCANNED_4K + PROCEDURAL_2K:
            e = export.set_entry(name)
            if e:
                sets[name] = e
        fixed = 0
        for a in data.get("assets", {}).values():
            for rec in a.get("material_slots", []):
                s = rec.get("set")
                if not s:
                    continue
                e = sets.get(s) or export.set_entry(s)
                if not e:
                    continue
                if rec.get("tile_m") is None and e.get("tile_m"):
                    rec["tile_m"] = e["tile_m"]
                    fixed += 1
                if not rec.get("textures"):
                    rec["textures"] = e.get("textures")
                if e.get("texel_density_px_per_m"):
                    rec["texel_density_px_per_m"] = e["texel_density_px_per_m"]
            dens = [r["texel_density_px_per_m"] for r in a.get("material_slots", []) if r.get("texel_density_px_per_m")]
            if dens and a.get("texel_density_px_per_m") is not None:
                dens.sort()
                a["texel_density_px_per_m"] = round(float(dens[len(dens) // 2]), 1)
        print("manifest: %d slots given a tile size" % fixed)
        return data
    export._locked_update(paths.manifest, upd)


if __name__ == "__main__":
    steps = sys.argv[1:] or ["rebake", "manifest"]
    if "rebake" in steps:
        rebake()
    if "manifest" in steps:
        patch_manifest()
