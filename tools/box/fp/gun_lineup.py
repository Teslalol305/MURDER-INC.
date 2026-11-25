"""Editor Python (run through MCP: python3 tools/box/mi_mcp.py py tools/box/fp/gun_lineup.py): the raw art of weapons round 4
laid out 250 m above the block for one picture of each, no game code in between: the five own guns (skeletal, in the reference
pose, muzzle to the right as seen by the camera lines it prints), and every part of the kit in a second row. It shows what the
weapons import made (meshes, slots, textures, the finish in daylight) apart from anything the game does with it.

  python3 mi_mcp.py py gun_lineup.py          lays them out and prints one "CAM <name> x,y,z,pitch,yaw,roll fov" line each
  then:  bash shot.sh out.jpg cam=<the line's numbers> fov=<fov> frames=40

Actors carry the tag MILineup; running it again replaces them; `clear()` removes them.
"""
import unreal

ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
Z = 25000.0
GUNS = [("chopper", "/Game/Weapons/Chopper/SK_Chopper"), ("nine", "/Game/Weapons/Nine/SK_Nine"),
        ("shorty", "/Game/Weapons/Shorty/SK_Shorty"), ("stretch", "/Game/Weapons/Stretch/SK_Stretch"),
        ("rattler", "/Game/Weapons/Rattler/SK_Rattler")]
PARTS = ["RedDot", "Scope4x", "Suppressor", "SuppressorPistol", "Compensator", "ForegripVertical", "ForegripVerticalWood",
         "ForegripAngled", "LaserModule", "MagRifleExt", "MagSmgExt", "MagPistolExt"]


def clear():
    n = 0
    for a in ACTORS.get_all_level_actors():
        if "MILineup" in [str(t) for t in a.tags]:
            ACTORS.destroy_actor(a)
            n += 1
    return n


def _cam(centre_x, centre_z, dist, label, fov=30.0):
    # seen from the gun's right side (+Y in Unreal is the gun's right): looking along -Y (yaw -90), the screen's right is +X
    print("CAM %s %.1f,%.1f,%.1f,0,-90,0 %.0f" % (label, centre_x, dist, centre_z, fov))


def lay():
    clear()
    made = []
    # a plain backdrop so the dark guns are not lost against the sky: a big pale card behind them (the -Y side)
    card = ACTORS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(300, -300, Z))
    card.static_mesh_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Cube"))
    card.set_actor_scale3d(unreal.Vector(30, 0.1, 15))
    card.tags = ["MILineup"]
    made.append(card)
    for i, (name, path) in enumerate(GUNS):
        mesh = unreal.load_asset(path)
        if mesh is None:
            print("MISSING %s" % path)
            continue
        x = i * 160.0
        a = ACTORS.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(x, 0, Z))
        a.skeletal_mesh_component.set_skinned_asset_and_update(mesh)
        a.tags = ["MILineup"]
        a.set_actor_label("lineup_" + name)
        made.append(a)
        b = mesh.get_bounds()
        _cam(x + b.origin.x, Z + b.origin.z, 150.0, name)
    for j, part in enumerate(PARTS):
        mesh = unreal.load_asset("/Game/Weapons/Parts/SM_Part_" + part)
        if mesh is None:
            print("MISSING part %s" % part)
            continue
        x = j * 60.0
        a = ACTORS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x, 0, Z + 150.0))
        a.static_mesh_component.set_static_mesh(mesh)
        a.tags = ["MILineup"]
        a.set_actor_label("lineup_" + part)
        made.append(a)
    _cam(5 * 60.0, Z + 150.0, 400.0, "parts", 40.0)
    print("LINEUP %d actors" % len(made))
    return len(made)


if __name__ == "__main__":
    lay()
