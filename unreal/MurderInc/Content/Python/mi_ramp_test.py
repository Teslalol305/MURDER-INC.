"""Vertex-colour decode ramp test (ART_BIBLE.md 3.3, BOX.md section 5): does the Wear decode of M_MI_Surface give
back the linear vertex colours the art exports?

A GLB strip of 11 quads whose COLOR_0 (linear, as glTF stores it) runs 0.0, 0.1 ... 1.0 is written here, imported
through the same Interchange path as the art (build_block.import_mesh), drawn with two test materials whose base
colour is the vertex colour (A: raw, B: decoded with pow(x, 2.2) as the master does) and captured as BaseColor (no
lighting, no tone mapping) into a float render target; the pixel at each quad centre is read back. Two calls, a
moment apart (the capture renders on a later frame):

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
W, H = 240, 120                    # render target pixels: 1 px per cm, ortho width 240 cm


def setup():
    glb = os.path.join(bb.project_dir("Saved"), "BuildBlock", GLB_NAME + ".glb")
    os.makedirs(os.path.dirname(glb), exist_ok=True)
    write_glb(glb)
    # The art's import path (Interchange glTF, Nanite, no glTF materials).
    saved_root = bb.ART_IN
    bb.ART_IN = os.path.dirname(glb)
    try:
        report = bb.import_mesh(GLB_NAME, {"glb": os.path.basename(glb)}, True)
    finally:
        bb.ART_IN = saved_root
    raw, decoded = ramp_material("M_Test_RampRaw", False), ramp_material("M_Test_RampDecoded", True)
    for actor in bb.ACTORS.get_all_level_actors():
        if actor.get_actor_label().startswith("RampTest"):
            bb.ACTORS.destroy_actor(actor)
    # glTF (x, y, z) lands as Unreal (x, z, y): the strip runs X 0..220, Z 0..20 in the plane Y = 0.
    for row, material in enumerate((raw, decoded)):
        actor = bb.ACTORS.spawn_actor_from_object(unreal.load_asset(bb.MESH_DIR + "/" + GLB_NAME), unreal.Vector(
            ORIGIN[0], ORIGIN[1], ORIGIN[2] + row * 40.0), bb.rotator())
        actor.set_actor_label("RampTest_%d" % row)
        actor.static_mesh_component.set_material(0, material)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    target = unreal.RenderingLibrary.create_render_target2d(world, W, H, unreal.TextureRenderTargetFormat.RTF_RGBA32F)
    capture = bb.ACTORS.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(
        ORIGIN[0] + 110.0, ORIGIN[1] - 500.0, ORIGIN[2] + 30.0), bb.rotator(yaw=90.0))
    capture.set_actor_label("RampTest_Capture")
    component = capture.capture_component2d
    component.set_editor_property("projection_type", unreal.CameraProjectionMode.ORTHOGRAPHIC)
    component.set_editor_property("ortho_width", float(W))
    component.set_editor_property("texture_target", target)
    component.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_BASE_COLOR)
    component.set_editor_property("capture_every_frame", False)
    component.capture_scene()
    _STATE.update(target=target, world=world)
    return "ramp set up: " + report


def read():
    """Base colour at each quad centre: strip A (raw vertex colour) row z 10, strip B (pow 2.2) row z 50."""
    pixels = unreal.RenderingLibrary.read_render_target_raw(_STATE["world"], _STATE["target"], False)
    if not pixels:
        return "nothing read"
    rows = []
    for k in range(STEPS):
        v = k / (STEPS - 1.0)
        column = 20 * k + 20
        a = pixels[(H // 2 + 20) * W + column]          # z = 10: 20 rows below the centre (z 30)
        b = pixels[(H // 2 - 20) * W + column]          # z = 50
        srgb = v * 12.92 if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055
        rows.append("%.1f  raw %.4f (sRGB(v) %.4f)  decoded %.4f (v %.4f, error %+.4f)" % (
            v, a.r, srgb, b.r, v, b.r - v))
    text = "\n".join(rows)
    with open(os.path.join(bb.project_dir("Saved"), "BuildBlock", "ramp.txt"), "w") as handle:
        handle.write(text + "\n")
    return text
