"""Vertex-colour decode ramp test (ART_BIBLE.md 3.3, BOX.md section 5): does the Wear decode of M_MI_Surface give
back the linear vertex colours the art exports?

A GLB strip of 11 quads whose COLOR_0 (linear, as glTF stores it) runs 0.0, 0.1 ... 1.0 is written here, imported
through the same Interchange path as the art (build_block.import_mesh), drawn with two test materials whose base
colour is the vertex colour (A: raw, B: decoded with pow(x, 2.2) as the master does) and captured as BaseColor (no
lighting, no tone mapping) into a float render target; the pixel at each quad centre is read back. Two runs of
the step, one tick apart (the capture renders on the next frame):

    import mi_ramp_test; mi_ramp_test.setup()     # import, materials, actors, capture
    mi_ramp_test.read()                           # the table, also written to Saved/BuildBlock/ramp.txt
"""
import json
import os
import struct

import unreal

import build_block as bb

STEPS = 11
GLB_NAME = "SM_Test_VertexRamp"
ORIGIN = (0.0, 0.0, 200000.0)      # far above the block, alone in the capture
QUAD = 20.0                        # cm per quad


def write_glb(path):
    """11 quads in a row along X (glTF metres, +Y up, facing +Z), COLOR_0 float RGBA = k / 10."""
    positions, colours, indices = [], [], []
    for k in range(STEPS):
        v = k / (STEPS - 1.0)
        x0, x1 = k * QUAD / 100.0, (k + 1) * QUAD / 100.0
        base = len(positions)
        for x, y in ((x0, 0.0), (x1, 0.0), (x1, QUAD / 100.0), (x0, QUAD / 100.0)):
            positions.append((x, y, 0.0))
            colours.append((v, v, v, 1.0))
        indices += [base, base + 1, base + 2, base, base + 2, base + 3]
    pos = b"".join(struct.pack("<3f", *p) for p in positions)
    col = b"".join(struct.pack("<4f", *c) for c in colours)
    idx = b"".join(struct.pack("<H", i) for i in indices)
    pad = lambda b: b + b"\0" * (-len(b) % 4)
    pos, col, idx = pad(pos), pad(col), pad(idx)
    blob = pos + col + idx
    gltf = {
        "asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": GLB_NAME}],
        "materials": [{"name": "MI_Test_Ramp"}],
        "meshes": [{"name": GLB_NAME, "primitives": [{"attributes": {"POSITION": 0, "COLOR_0": 1}, "indices": 2,
                                                       "material": 0}]}],
        "buffers": [{"byteLength": len(blob)}],
        "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": len(pos)},
                        {"buffer": 0, "byteOffset": len(pos), "byteLength": len(col)},
                        {"buffer": 0, "byteOffset": len(pos) + len(col), "byteLength": len(idx)}],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": len(positions), "type": "VEC3",
             "min": [0.0, 0.0, 0.0], "max": [STEPS * QUAD / 100.0, QUAD / 100.0, 0.0]},
            {"bufferView": 1, "componentType": 5126, "count": len(colours), "type": "VEC4"},
            {"bufferView": 2, "componentType": 5123, "count": len(indices), "type": "SCALAR"}],
    }
    js = json.dumps(gltf).encode()
    js += b" " * (-len(js) % 4)
    body = struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(blob), 0x004E4942) + blob
    with open(path, "wb") as handle:
        handle.write(struct.pack("<III", 0x46546C67, 2, 12 + len(body)) + body)


def ramp_material(name, decode):
    path = bb.MAT_DIR + "/" + name
    if bb.ASSETS.does_asset_exist(path):
        material = unreal.load_asset(path)
        bb.LIB.delete_all_material_expressions(material)
    else:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, bb.MAT_DIR, unreal.Material,
                                                                           unreal.MaterialFactoryNew())
    vc = bb.expr(material, unreal.MaterialExpressionVertexColor, -600, 0)
    out = vc
    if decode:
        power = bb.expr(material, unreal.MaterialExpressionPower, -300, 0)
        bb.LIB.connect_material_expressions(vc, "", power, "Base")
        bb.LIB.connect_material_expressions(bb.expr(material, unreal.MaterialExpressionConstant, -500, 100, r=2.2), "",
                                            power, "Exponent")
        out = power
    bb.LIB.connect_material_property(out, "", unreal.MaterialProperty.MP_BASE_COLOR)
    bb.setp(material, "two_sided", True)
    bb.LIB.recompile_material(material)
    bb.ASSETS.save_asset(path, only_if_is_dirty=False)
    return material


_STATE = {}


def setup():
    glb = os.path.join(bb.project_dir("Saved"), "BuildBlock", GLB_NAME + ".glb")
    os.makedirs(os.path.dirname(glb), exist_ok=True)
    write_glb(glb)
    # The art's import path (Interchange glTF, Nanite, no glTF materials), from a manifest-like entry.
    saved_root = bb.ART_IN
    bb.ART_IN = os.path.dirname(glb)
    try:
        bb.import_mesh(GLB_NAME, {"glb": os.path.basename(glb)}, True)
    finally:
        bb.ART_IN = saved_root
    raw, decoded = ramp_material("M_Test_RampRaw", False), ramp_material("M_Test_RampDecoded", True)
    for actor in bb.ACTORS.get_all_level_actors():
        if actor.get_actor_label().startswith("RampTest"):
            bb.ACTORS.destroy_actor(actor)
    mesh_path = bb.MESH_DIR + "/" + GLB_NAME
    # Two strips facing down (-Z; glTF +Z is Unreal +Y... the strip is turned to face the capture below).
    actors = []
    for row, material in enumerate((raw, decoded)):
        actor = bb.ACTORS.spawn_actor_from_object(unreal.load_asset(mesh_path), unreal.Vector(
            ORIGIN[0], ORIGIN[1] + row * 40.0, ORIGIN[2]), bb.rotator())
        actor.set_actor_label("RampTest_%d" % row)
        actor.static_mesh_component.set_material(0, material)
        actors.append(actor)
    box = actors[0].get_actor_bounds(False)
    target = unreal.RenderingLibrary.create_render_target2d(bb.ACTORS.get_all_level_actors()[0].get_world(), 1100, 400,
                                                            unreal.TextureRenderTargetFormat.RTF_RGBA32F)
    capture = bb.ACTORS.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 0), bb.rotator())
    capture.set_actor_label("RampTest_Capture")
    component = capture.capture_component2d
    component.set_editor_property("projection_type", unreal.CameraProjectionMode.ORTHOGRAPHIC)
    component.set_editor_property("ortho_width", STEPS * QUAD)
    component.set_editor_property("texture_target", target)
    component.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_BASE_COLOR)
    component.set_editor_property("capture_every_frame", False)
    _STATE.update(target=target, actors=actors, capture=capture, box=box)
    return "ramp set up; bounds %s" % (box,)


def aim_and_capture():
    """Point the orthographic capture at the strips (found from their bounds), capture once."""
    centre, extent = _STATE["box"]
    lo, hi = _STATE["actors"][0].get_actor_bounds(False), _STATE["actors"][1].get_actor_bounds(False)
    mid = (lo[0] + hi[0]) * 0.5
    # The strips are flat in one axis: look along it.
    flat = min(range(3), key=lambda i: (lo[1].x, lo[1].y, lo[1].z)[i])
    eye = unreal.Vector(mid.x, mid.y, mid.z)
    rot = bb.rotator()
    if flat == 2:
        eye.z -= 500.0
        rot = bb.rotator(pitch=90.0)
    elif flat == 1:
        eye.y -= 500.0
        rot = bb.rotator(yaw=90.0)
    else:
        eye.x -= 500.0
    capture = _STATE["capture"]
    capture.set_actor_location_and_rotation(eye, rot, False, True)
    component = capture.capture_component2d
    component.set_editor_property("ortho_width", max(lo[1].x, lo[1].y, lo[1].z) * 2.0 + 10.0)
    component.capture_scene()
    _STATE["flat"] = flat
    return "capture along axis %d from %s" % (flat, eye)


def read():
    world = bb.ACTORS.get_all_level_actors()[0].get_world()
    target = _STATE["target"]
    rows = []
    found = {}
    for y in range(0, 400, 4):
        line = [unreal.RenderingLibrary.read_render_target_raw_pixel(world, target, x, y) for x in range(0, 1100, 10)]
        values = [round(c.r, 3) for c in line]
        if max(values) > 0.0:
            found.setdefault(len(found), values)
    lines = ["row %d: %s" % (k, v) for k, v in found.items()]
    with open(os.path.join(bb.project_dir("Saved"), "BuildBlock", "ramp.txt"), "w") as handle:
        handle.write("\n".join(lines))
    return "\n".join(lines[:6]) or "nothing captured"
