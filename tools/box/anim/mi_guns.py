"""The pack rifles assembled from their sockets, for looking at them (editor Python, scratch project, MCP 8003).

    import sys; sys.path.insert(0, "<dir of this file>"); import mi_guns as M
    M.studio()                                   # dark studio: floor, backdrop, key / fill / rim lights
    M.rifle("Default", ["scope", "silencer", "grip_vertical", "laser"], loc=(0, 0, 100), yaw=-90, label="G")
    M.cam_at("G", eye_local=(-60, 20, 15))       # 'x,y,z,pitch,yaw,roll' looking at the gun from a point in gun space

The assembly is the game's (UMIGunAssembly, LOADOUT.md 6.2): the base mesh is the length's Combined rifle, or its
Combined_Folded twin (irons folded) whenever an optic is fitted; parts snap to the sockets ue_import_guns.py wrote
(identity: the parts are modelled in the rifle's frame); the magazine hangs from MagHinge; the clear magazine is the
skeletal SK_TFA_AR_Magazine_Transparent with one SM_TFA_AR_Bullet on each of its Bullet_001.. bones up to the rounds
left (RoundsShown).
"""
import math

import unreal

W = "/Game/ThirdParty/InfimaTFA/Weapon"
ATT = W + "/Attachments"
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
PARTS = {"scope": ("SM_TFA_AR_ATT_Scope", "Optic"), "silencer": ("SM_TFA_AR_ATT_Silencer", "MuzzleMount"),
         "grip_vertical": ("SM_TFA_AR_ATT_Grip_Vertical", "Underbarrel"),
         "grip_angled": ("SM_TFA_AR_ATT_Grip_Angled", "Underbarrel"), "laser": ("SM_TFA_AR_ATT_Laser", "Laser")}
SNAP = unreal.AttachmentRule.SNAP_TO_TARGET
TAG = "MIGuns"
DEPLETION = W + "/Anims/Common/A_TFA_AR_Magazine_FireDepletion"


def clear():
    for a in ACTORS.get_all_level_actors():
        if TAG in [str(t) for t in a.tags] or "MIStage" in [str(t) for t in a.tags] or "MIRig" in [str(t) for t in a.tags]:
            ACTORS.destroy_actor(a)


def _tag(a, label=None):
    a.tags = [TAG]
    if label:
        a.set_actor_label(label)
    return a


def dark_material(name="M_MI_StudioDark", value=0.018, rough=0.55):
    path = "/Game/Studio/" + name
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        return unreal.load_asset(path)
    mel = unreal.MaterialEditingLibrary
    m = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, "/Game/Studio", unreal.Material,
                                                                 unreal.MaterialFactoryNew())
    c = mel.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -300, 0)
    c.set_editor_property("constant", unreal.LinearColor(value, value, value * 1.05, 1))
    r = mel.create_material_expression(m, unreal.MaterialExpressionConstant, -300, 200)
    r.set_editor_property("r", rough)
    mel.connect_material_property(c, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.recompile_material(m)
    unreal.EditorAssetLibrary.save_loaded_asset(m)
    return m


def studio(exposure=5.0, key=8.0, backdrop=True, sun_yaw=-50.0, sun_pitch=-38.0):
    clear()
    dark = dark_material()
    floor = ACTORS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 0))
    floor.static_mesh_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Plane"))
    floor.set_actor_scale3d(unreal.Vector(40, 40, 1))
    floor.static_mesh_component.set_material(0, dark)
    _tag(floor, "Floor")
    if backdrop:
        for i, (loc, sc) in enumerate((((0, -260, 250), (40, 0.2, 5)), ((0, 260, 250), (40, 0.2, 5)))):
            w = ACTORS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*loc))
            w.static_mesh_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Cube"))
            w.set_actor_scale3d(unreal.Vector(*sc))
            w.static_mesh_component.set_material(0, dark)
            _tag(w, "Backdrop%d" % i)
    sun = ACTORS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 400),
                                        unreal.Rotator(roll=0, pitch=sun_pitch, yaw=sun_yaw))
    sun.light_component.set_editor_property("intensity", key)
    _tag(sun, "Key")
    _tag(ACTORS.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0)), "Atmos")
    sky = ACTORS.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 300))
    sky.light_component.set_editor_property("real_time_capture", True)
    _tag(sky, "Sky")
    for i, (loc, inten, col) in enumerate((((-120, 160, 190), 9000.0, (1.0, 0.92, 0.85)),
                                          ((140, -150, 150), 5000.0, (0.75, 0.85, 1.0)))):
        p = ACTORS.spawn_actor_from_class(unreal.RectLight, unreal.Vector(*loc))
        lc = p.light_component
        lc.set_editor_property("intensity", inten)
        lc.set_light_color(unreal.LinearColor(col[0], col[1], col[2], 1.0))
        lc.set_editor_property("source_width", 120.0)
        lc.set_editor_property("source_height", 120.0)
        lc.set_editor_property("attenuation_radius", 900.0)
        p.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*loc), unreal.Vector(0, 0, 100)), False)
        _tag(p, "Rect%d" % i)
    pp = ACTORS.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0, 0, 0))
    pp.set_editor_property("unbound", True)
    s = pp.get_editor_property("settings")
    for k, v in dict(override_auto_exposure_method=True, auto_exposure_method=unreal.AutoExposureMethod.AEM_MANUAL,
                     override_auto_exposure_bias=True, auto_exposure_bias=exposure).items():
        s.set_editor_property(k, v)
    pp.set_editor_property("settings", s)
    _tag(pp, "PP")
    return "studio"


def _skel(mesh, loc, rot, label, anim=None, t=0.0):
    a = ACTORS.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(*loc), rot)
    _tag(a, label)
    c = a.skeletal_mesh_component
    c.set_skinned_asset_and_update(unreal.load_asset(mesh))
    if anim:
        c.set_update_animation_in_editor(True)
        c.override_animation_data(unreal.load_asset(anim), False, False, float(t), 0.0)
    return a


def _static(mesh, label):
    a = ACTORS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 0))
    _tag(a, label)
    a.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    a.static_mesh_component.set_static_mesh(unreal.load_asset(mesh))
    return a


def _attach(child, parent, socket):
    child.attach_to_actor(parent, socket, SNAP, SNAP, unreal.AttachmentRule.KEEP_WORLD, False)


def base_mesh(length, parts=()):
    """The game's variant rule: irons folded (the _Folded mesh) whenever an optic other than the irons is fitted."""
    folded = "scope" in parts
    return "%s/SK_TFA_AR_%s_Combined%s" % (W, length, "_Folded" if folded else "")


def magazine(parent, label, kind="standard", rounds=30, socket="MagHinge"):
    out = []
    if kind == "clear":
        clip = unreal.load_asset(DEPLETION)
        t = 0.0
        if clip is not None:   # one frame per round fired: frame = size - rounds left
            t = min(clip.get_play_length(), (30 - int(rounds)) / 30.0)
        m = _skel(W + "/SK_TFA_AR_Magazine_Transparent", (0, 0, 0), unreal.Rotator(0, 0, 0), label + "_MagClear",
                  DEPLETION if clip is not None else None, t)
        _attach(m, parent, socket)
        out.append(m)
        for i in range(1, 31):
            b = _static(ATT + "/SM_TFA_AR_Bullet", "%s_Round%02d" % (label, i))
            _attach(b, m, "Bullet_%03d" % i)
            out.append(b)
    elif kind:
        m = _static(ATT + "/SM_TFA_AR_Magazine_Full", label + "_Mag")
        _attach(m, parent, socket)
        out.append(m)
    return out


def rifle(length="Default", parts=(), loc=(0, 0, 100), yaw=-90.0, pitch=0.0, roll=0.0, label="G", mag="standard",
          rounds=30, anim=None, t=0.0, parent=None, parent_socket=None):
    rot = unreal.Rotator(roll=roll, pitch=pitch, yaw=yaw)
    g = _skel(base_mesh(length, parts), loc, rot, label, anim, t)
    if parent is not None:
        _attach(g, parent, parent_socket)
    out = [g]
    for p in parts:
        mesh, sock = PARTS[p]
        a = _static(ATT + "/" + mesh, "%s_%s" % (label, p))
        _attach(a, g, sock)
        out.append(a)
    out += magazine(g, label, mag, rounds)
    return [a.get_actor_label() for a in out]


def actor(label):
    for a in ACTORS.get_all_level_actors():
        if a.get_actor_label() == label:
            return a
    raise KeyError(label)


def socket_world(label, socket):
    a = actor(label)
    c = a.get_component_by_class(unreal.SkeletalMeshComponent) or a.get_component_by_class(unreal.StaticMeshComponent)
    return c.get_socket_transform(socket, unreal.RelativeTransformSpace.RTS_WORLD)


def look(eye, target):
    e = unreal.Vector(*eye)
    r = unreal.MathLibrary.find_look_at_rotation(e, unreal.Vector(*target))
    return "%.3f,%.3f,%.3f,%.3f,%.3f,%.3f" % (e.x, e.y, e.z, r.pitch, r.yaw, r.roll)


def cam_at(label, eye_local, target_local=(0, 14, 0)):
    """Camera at a point given in the gun's own frame (cm; +Y muzzle, +X left, +Z up) looking at another."""
    tr = actor(label).get_actor_transform()
    e = tr.transform_location(unreal.Vector(*eye_local))
    t = tr.transform_location(unreal.Vector(*target_local))
    return look((e.x, e.y, e.z), (t.x, t.y, t.z))


def gap_report(label):
    """World positions of the mount sockets and of the parts' own sockets (for the offset checks)."""
    out = {}
    for s in ("Optic", "MuzzleMount", "Muzzle", "Underbarrel", "Laser", "MagHinge", "SightRear", "SightFront"):
        t = socket_world(label, s).translation
        out[s] = [round(t.x, 2), round(t.y, 2), round(t.z, 2)]
    return out
