"""Effect material diagnosis (review 2026-11-23: the translucent puffs never showed in a picture).

Run in the live editor (L_Block open, no play in editor):  python3 mi_mcp.py py tools/box/fp/fx_diag.py
Builds four test materials under /Game/FX/Diag and puts five 50 cm cards 3 m in front of the camera
(-2900, 80, 170) looking +X, left to right: translucent constant, translucent + DepthFade, translucent + the smoke
Custom node, M_FX_Smoke itself (Opacity 1), M_FX_Flash (additive, the control). Then:
  bash shot.sh <out.jpg> cam=-2900,80,170,0,0,0 fov=50 frames=40
fx_diag.py clean removes the cards. Nothing here is committed content.
"""
import os
import sys

import unreal

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "/project/ue/repo-gameplay/tools/box/fp"
sys.path.insert(0, HERE)
import mi_fp_import as F  # noqa: E402

D = "/Game/FX/Diag"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def mat(name, custom=False, depth=False):
    p = D + "/" + name
    m = F._material(p)
    em = F._expr(m, unreal.MaterialExpressionConstant3Vector, -400, 0, constant=unreal.LinearColor(1500.0, 1400.0, 1300.0, 1.0))
    F.MEL.connect_material_property(em, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    op = F._expr(m, unreal.MaterialExpressionConstant, -600, 200, r=0.8)
    if custom:
        uv = F._expr(m, unreal.MaterialExpressionTextureCoordinate, -900, 200)
        c = F._custom(m, -600, 300, F.SMOKE_HLSL, ["UV", "Seed", "Erode"])
        F.MEL.connect_material_expressions(uv, "", c, "UV")
        F.MEL.connect_material_expressions(F._expr(m, unreal.MaterialExpressionConstant, -900, 300, r=3.0), "", c, "Seed")
        F.MEL.connect_material_expressions(F._expr(m, unreal.MaterialExpressionConstant, -900, 380, r=0.0), "", c, "Erode")
        op = c
    if depth:
        df = F._expr(m, unreal.MaterialExpressionDepthFade, -200, 200)
        df.set_editor_property("fade_distance_default", 40.0)
        F.MEL.connect_material_expressions(op, "", df, "Opacity")
        op = df
    F.MEL.connect_material_property(op, "", unreal.MaterialProperty.MP_OPACITY)
    F._set(m, blend_mode=unreal.BlendMode.BLEND_TRANSLUCENT, shading_model=unreal.MaterialShadingModel.MSM_UNLIT, two_sided=True)
    return F._finish(m, p)


def clean():
    for a in EAS.get_all_level_actors():
        if a.actor_has_tag("MIDiag"):
            EAS.destroy_actor(a)


def main():
    clean()
    paths = [mat("M_D_Const"), mat("M_D_Depth", depth=True), mat("M_D_Custom", custom=True),
             "/Game/FX/M_FX_Smoke", "/Game/FX/M_FX_Flash"]
    plane = unreal.load_asset("/Engine/BasicShapes/Plane")
    out = []
    for i, p in enumerate(paths):
        a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(-2600.0, 80.0 + (i - 2) * 60.0, 170.0),
                                       unreal.Rotator(roll=0.0, pitch=90.0, yaw=0.0))
        a.tags = ["MIDiag"]
        c = a.static_mesh_component
        c.set_mobility(unreal.ComponentMobility.MOVABLE)
        c.set_static_mesh(plane)
        c.set_world_scale3d(unreal.Vector(0.5, 0.5, 0.5))
        m = unreal.load_asset(p)
        if p.endswith("M_FX_Smoke") or p.endswith("M_FX_Flash"):
            mid = c.create_dynamic_material_instance(0, m)
            mid.set_scalar_parameter_value("Opacity", 1.0)
            mid.set_scalar_parameter_value("Seed", 3.0)
            mid.set_scalar_parameter_value("Intensity", 3000.0)
            mid.set_vector_parameter_value("Color", unreal.LinearColor(0.5, 0.48, 0.45, 1.0))
        else:
            c.set_material(0, m)
        out.append((p, str(a.get_actor_location())))
    return out


if os.environ.get("MI_DIAG") == "clean" or "clean" in getattr(sys, "argv", []):
    clean()
    RESULT = "cleaned"
else:
    RESULT = main()
RESULT
