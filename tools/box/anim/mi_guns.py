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


def studio(exposure=5.0, key=8.0, backdrop=True, sun_yaw=-50.0, sun_pitch=-38.0, target=(0, 0, 100), back=0.018):
    clear()
    dark = dark_material() if back <= 0.02 else dark_material("M_MI_StudioGrey", back, 0.7)
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
        loc = (loc[0] + target[0], loc[1] + target[1], loc[2] + target[2] - 100)
        p.set_actor_location(unreal.Vector(*loc), False, False)
        p.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*loc), unreal.Vector(*target)), False)
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


# ---------------------------------------------------------------- first person (ANIMATION.md 9: the camera recipe)
ARMS = "/Game/Characters/RuleArms/SK_RuleArms"
CHAR = "/Game/ThirdParty/InfimaTFA/Character/FP/"
WEPA = W + "/Anims/FP/"
# The pack's first-person clips keep the head joint still at (0, 0.66, 162.58) in component space (every FP clip,
# measured) and, in Aim_Pose and Fire_Aimed, put the iron sight line through it (0.57 cm below, parallel to +Y).
# The camera is that point on the sight line: component (0, 0.66, 162.0), looking along +Y, no roll.
EYE = (0.0, 0.66, 162.0)


# First-person (arms and gun) field of view, vertical degrees, blended by Ads (ANIMATION.md 9). Hip 54 (84.3 h at
# 16:9); aimed it narrows so the sight picture reads at the size of current shooters: irons 38 (63.0 h), any optic
# 32 (54.0 h). The world FOV stays the rules' (74 / 52 aimed / 30 scope).
FP_FOV_V = {"hip": 54.0, "irons": 38.0, "optic": 32.0}


def fov_h(v_deg, aspect=16.0 / 9.0):
    return math.degrees(2.0 * math.atan(math.tan(math.radians(v_deg) / 2.0) * aspect))


def fp_fov(ads=0.0, optic=False, aspect=16.0 / 9.0):
    """The recipe's arms FOV, horizontal degrees, at Ads 0..1 (linear in the vertical angle, as the rules blend)."""
    v = FP_FOV_V["hip"] + (FP_FOV_V["optic" if optic else "irons"] - FP_FOV_V["hip"]) * max(0.0, min(1.0, ads))
    return fov_h(v, aspect)


# The pack rifle's two magazine bones during its reloads (A_TFA_FP_WEP_AR_*, measured every 1/15 s with AnimPose):
# Magazine carries the old magazine, Magazine_Reserve the fresh one from the chest pouch (36 cm from the seat in
# gun space, where it rests outside the reloads). In first person there is no pouch: hide a magazine that rests there.
#   reserve: the left hand has the fresh magazine from this time (before it, hide Magazine_Reserve's mesh)
#   out:     the old magazine leaves the seat
#   drop:    True = it falls free (spawn a physics SM_TFA_AR_Magazine_Empty / _Full at the Magazine bone with the
#            bone's velocity at `out` and hide the bone's mesh to the end); False = retained, carried to the pouch
#   stow:    retained only: the hand lets go of it in the pouch (hide the Magazine bone's mesh from here)
#   seated:  the fresh magazine is home (Magazine_Reserve on the seat to the end of the clip)
# At the end of every clip the bones swap back (the idle has Magazine on the seat, Magazine_Reserve in the pouch):
# show the magazine mesh on Magazine (MagHinge) with the fresh magazine's rounds, hide Magazine_Reserve's.
RELOAD_MAGS = {
    "A_TFA_FP_WEP_AR_Reload": {"reserve": 0.267, "out": 0.867, "drop": False, "stow": 2.067, "seated": 1.40},
    "A_TFA_FP_WEP_AR_Reload_Empty_Retain": {"reserve": 0.267, "out": 0.867, "drop": False, "stow": 2.133,
                                            "seated": 1.40},
    "A_TFA_FP_WEP_AR_Reload_Empty": {"reserve": 0.267, "out": 0.333, "drop": True, "stow": None, "seated": 1.333},
    "A_TFA_FP_WEP_AR_Reload_Quick": {"reserve": 0.267, "out": 0.40, "drop": True, "stow": None, "seated": 1.467},
}


def mag_shown(wep, t):
    """(old magazine on Magazine shown, fresh one on Magazine_Reserve shown) at t of a weapon reload clip."""
    r = RELOAD_MAGS.get(wep)
    if r is None:
        return True, False
    old = t < r["out"] if r["drop"] else t < r["stow"]
    return old, t >= r["reserve"]


def fp(clip, t, wep=None, length="Default", parts=(), mesh=ARMS, mag="standard", rounds=30, reserve=False,
       label="FP", sight=None):
    """Arms (or the mannequin) playing a pack FP clip at t with the pack rifle on ik_hand_gun (identity) playing
    the matching weapon clip; returns the camera 'x,y,z,pitch,yaw,roll' of the recipe. sight: None = the recipe's
    eye; 'irons' / 'scope' = the eye moved onto that sight's axis (the aimed-state correction for the optic).
    The magazines follow RELOAD_MAGS (a dropped or stowed magazine hidden, the reserve shown once in hand); the
    picture's FOV is fp_fov(Ads, optic)."""
    a = _skel(mesh, (0, 0, 0), unreal.Rotator(0, 0, 0), label, CHAR + clip, t)
    g_labels = rifle(length, parts, loc=(0, 0, 0), yaw=0.0, label=label + "_Gun",
                     anim=(WEPA + wep) if wep else None, t=t, parent=a, parent_socket="ik_hand_gun")
    old_shown, res_shown = mag_shown(wep, t)
    if not old_shown:
        for x in ACTORS.get_all_level_actors():
            if x.get_actor_label().startswith(label + "_Gun_Mag"):
                x.set_actor_hidden_in_game(True)
                x.set_is_temporarily_hidden_in_editor(True)
    if reserve and res_shown:
        m = _static(ATT + "/SM_TFA_AR_Magazine_Full", label + "_Reserve")
        _attach(m, actor(label + "_Gun"), "Magazine_Reserve")
    eye = EYE
    if sight == "irons":
        s = socket_world(label + "_Gun", "SightRear").translation
        eye = (s.x, EYE[1], s.z)
    elif sight == "scope":
        s = socket_world(label + "_scope_part", "SightEye").translation if False else \
            actor(label + "_Gun_scope").static_mesh_component.get_socket_location("SightEye")
        eye = (s.x, EYE[1], s.z)
    return "%.3f,%.3f,%.3f,0,90,0" % eye


def near_clip(cm=1.0):
    unreal.SystemLibrary.execute_console_command(None, "r.SetNearClipPlane %g" % cm)
