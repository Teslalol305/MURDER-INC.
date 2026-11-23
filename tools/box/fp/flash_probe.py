# The player's muzzle flash diagnosis (polish pass): run in the play-in-editor world through mi_mcp.py py.
# MODE (first line replaced by the caller): "list" prints every visible effect card of the effects' host actor
# (distance from the eye, screen point, scale, material); "cards" spawns probe cards in front of the eye at 20, 40, 80,
# 150 and 400 cm (flash material, emissive 40,000 nits, same angular size) in the upper half of the view, and opaque
# cubes in the same places below the centre; "clear" removes the probes.
MODE = "list"
import math
import unreal

w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pcm = unreal.GameplayStatics.get_player_camera_manager(w, 0)
eye, rot = pcm.get_camera_location(), pcm.get_camera_rotation()
fwd, right, up = rot.get_forward_vector(), rot.get_right_vector(), rot.get_up_vector()
pc = unreal.GameplayStatics.get_player_controller(w, 0)
out = []


def screen(p):
    r = unreal.GameplayStatics.project_world_to_screen(pc, p, False)
    s = r[1] if isinstance(r, tuple) else r
    return "(%.0f, %.0f)" % (s.x, s.y) if s is not None else "off"


if MODE == "list":
    for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor):
        if a.get_class().get_name() != "Actor":
            continue
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            if not c.is_visible():
                continue
            p = c.get_world_location()
            m = c.get_material(0)
            out.append("card %s mat %s at %.1f cm from the eye, ahead %.1f, screen %s, scale %s, fp %s" % (
                c.get_name(), m.get_name() if m else None, (p - eye).length(), (p - eye).dot(fwd), screen(p),
                c.get_world_scale().to_tuple() if hasattr(c.get_world_scale(), "to_tuple") else c.get_world_scale(),
                c.get_editor_property("first_person_primitive_type") if hasattr(c, "get_editor_property") else "?"))
    out.append("eye %s fwd %s" % (eye, fwd))
elif MODE == "cards":
    flash = unreal.load_asset("/Game/FX/M_FX_Flash")
    plane = unreal.load_asset("/Engine/BasicShapes/Plane")
    cube = unreal.load_asset("/Engine/BasicShapes/Cube")
    # Python cannot spawn actors in the play world here: the probes are components added to the effects' host actor.
    host = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor) if a.get_class().get_name() == "Actor"
            and a.get_components_by_class(unreal.StaticMeshComponent)][0]
    for i, d in enumerate((20.0, 40.0, 80.0, 150.0, 400.0)):
        x = (i - 2) * 0.22
        for kind, yk in (("card", 0.22), ("cube", -0.08)):
            p = eye + fwd * d + right * (d * x) + up * (d * yk)
            c = host.add_component_by_class(unreal.StaticMeshComponent, False, unreal.Transform(), False)
            c.component_tags = ["MIFlashProbe"]
            c.set_mobility(unreal.ComponentMobility.MOVABLE)
            c.set_absolute(True, True, True)
            c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            c.set_static_mesh(plane if kind == "card" else cube)
            k = d * 0.07 / 100.0
            r = unreal.Rotator(0, 0, 0)
            if kind == "card":
                mid = unreal.KismetMaterialLibrary.create_dynamic_material_instance(w, flash)
                mid.set_scalar_parameter_value("Intensity", 40000.0)
                mid.set_scalar_parameter_value("Mode", 0.0)
                c.set_material(0, mid)
                r = unreal.MathLibrary.make_rot_from_z(eye - p)   # the plane's normal (+Z) toward the eye
            else:
                k *= 0.5
            c.set_world_location_and_rotation(p, r, False, False)
            c.set_world_scale3d(unreal.Vector(k, k, k if kind == "cube" else 1.0))
            c.set_visibility(True)
            out.append("%s %.0f cm at screen %s" % (kind, d, screen(p)))
else:
    n = 0
    for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor):
        for c in a.get_components_by_tag(unreal.StaticMeshComponent, "MIFlashProbe"):
            c.destroy_component(c)
            n += 1
    out.append("removed %d" % n)
"\n".join(out)
