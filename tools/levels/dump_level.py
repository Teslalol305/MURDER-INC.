#!/usr/bin/env python3
"""A text dump of a built level, to prove that a refactored builder makes the same map (MAPS.md lane B, item A0).

Two halves that write two diffable text files:

1. INSIDE the Unreal editor (the level to dump is open): one sorted line per actor, with its class, name, label, folder,
   transform, tags, and for every mesh component the mesh asset, the first materials and, for an instanced component,
   the instance count and a digest of all instance transforms (a facade kit has thousands of instances, so they are
   hashed, not listed). Run it with
       MI_DUMP_OUT=<file> bash tools/box/... mi_mcp.py py tools/levels/dump_level.py
   or from the editor's Python console: import dump_level; dump_level.dump_actors("<file>").
2. OUTSIDE the editor (plain python3): the art input the builder reads, as one line per manifest asset (name plus a
   digest of its entry) and one line per placement, with the digests of the whole files:
       python3 tools/levels/dump_level.py art <art-in folder> <file>

The files are plain text, sorted, with numbers rounded to 3 decimals, so `diff` shows exactly what moved. A later
`build_level.py --level block` is proved identical when both files come out byte for byte the same.
"""
import hashlib
import json
import os
import sys


def _r(v):
    return round(float(v) + 0.0, 3)


def _vec(v):
    return "%g,%g,%g" % (_r(v.x), _r(v.y), _r(v.z))


def _xf(t):
    return "loc=%s rot=%g,%g,%g scale=%s" % (
        _vec(t.translation), _r(t.rotation.rotator().pitch), _r(t.rotation.rotator().yaw),
        _r(t.rotation.rotator().roll), _vec(t.scale3d))


def _digest(parts):
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode())
        h.update(b"\n")
    return h.hexdigest()[:16]


def _component_line(unreal, comp):
    cls = comp.get_class().get_name()
    mesh = ""
    try:
        m = comp.get_editor_property("static_mesh")
        mesh = m.get_path_name() if m else "None"
    except Exception:
        pass
    mats = []
    try:
        for i in range(min(comp.get_num_materials(), 6)):
            mm = comp.get_material(i)
            mats.append(mm.get_path_name() if mm else "None")
    except Exception:
        pass
    extra = ""
    if "Instanced" in cls:
        n = comp.get_instance_count()
        xs = []
        for i in range(n):
            t = comp.get_instance_transform(i, True)
            xs.append(_xf(t))
        extra = " instances=%d inst_digest=%s" % (n, _digest(sorted(xs)))
    rel = ""
    try:
        rel = _xf(comp.get_relative_transform())
    except Exception:
        pass
    flags = []
    for prop in ("collision_enabled", "mobility"):
        try:
            flags.append("%s=%s" % (prop, comp.get_editor_property(prop)))
        except Exception:
            pass
    return "    comp %s %s mesh=%s mats=%s %s%s %s" % (
        comp.get_name(), cls, mesh, "|".join(mats), rel, extra, " ".join(flags))


def dump_actors(path):
    import unreal
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = sub.get_all_level_actors()
    blocks = []
    for a in actors:
        try:
            tags = sorted(str(t) for t in a.tags)
            head = "ACTOR %s | class=%s | label=%s | folder=%s | %s | tags=%s" % (
                a.get_name(), a.get_class().get_name(), a.get_actor_label(), a.get_folder_path(),
                _xf(a.get_actor_transform()), ",".join(tags))
            comps = []
            for c in a.get_components_by_class(unreal.PrimitiveComponent):
                comps.append(_component_line(unreal, c))
            comps.sort()
            blocks.append((a.get_name(), head + "\n" + "\n".join(comps)))
        except Exception as e:
            blocks.append((a.get_name(), "ACTOR %s | dump error %s" % (a.get_name(), e)))
    blocks.sort(key=lambda b: b[0])
    world = unreal.EditorLevelLibrary.get_editor_world()
    out = ["# level=%s actors=%d" % (world.get_path_name() if world else "?", len(blocks))]
    out += [b[1] for b in blocks]
    with open(path, "w") as f:
        f.write("\n".join(out) + "\n")
    return "dumped %d actors to %s" % (len(blocks), path)


def dump_art(art_in, path):
    lines = []
    man_path = os.path.join(art_in, "manifest.json")
    raw = open(man_path, "rb").read()
    lines.append("manifest.json sha256=%s bytes=%d" % (hashlib.sha256(raw).hexdigest(), len(raw)))
    man = json.loads(raw)
    for key in sorted(man):
        if key != "assets":
            lines.append("manifest.%s digest=%s" % (key, _digest([json.dumps(man[key], sort_keys=True)])))
    for name in sorted(man.get("assets", {})):
        lines.append("asset %s digest=%s" % (name, _digest([json.dumps(man["assets"][name], sort_keys=True)])))
    pdir = os.path.join(art_in, "placements")
    for fn in sorted(os.listdir(pdir)):
        pr = open(os.path.join(pdir, fn), "rb").read()
        lines.append("placements/%s sha256=%s bytes=%d" % (fn, hashlib.sha256(pr).hexdigest(), len(pr)))
        data = json.loads(pr)
        insts = data.get("instances") if isinstance(data, dict) else data
        if isinstance(insts, list):
            for i, e in enumerate(insts):
                lines.append("placement %s %05d %s" % (fn, i, json.dumps(e, sort_keys=True, separators=(",", ":"))))
        elif isinstance(data, dict):
            for k in sorted(data):
                lines.append("placement %s %s %s" % (fn, k, json.dumps(data[k], sort_keys=True, separators=(",", ":"))[:2000]))
    for sub in ("glb", "textures"):
        d = os.path.join(art_in, sub)
        if os.path.isdir(d):
            n = 0
            for root, _, files in os.walk(d):
                for fn in files:
                    n += 1
            lines.append("%s files=%d" % (sub, n))
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return "dumped art lines=%d to %s" % (len(lines), path)


try:
    import unreal  # noqa: F401
    if os.environ.get("MI_DUMP_OUT"):
        _result = dump_actors(os.environ["MI_DUMP_OUT"])
except ImportError:
    pass

if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "art":
        print(dump_art(sys.argv[2], sys.argv[3]))
    else:
        print(__doc__)
