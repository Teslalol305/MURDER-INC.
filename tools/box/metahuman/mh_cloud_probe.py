# Run inside the MetaHuman scratch editor (py.sh mh_cloud_probe.py), started by editor.sh (which passes
# -NoMetaHumanAccountPortalLoginFallback, so nothing opens an Epic login page): ask for the two cloud services the
# assembly gate needs, without any credentials, and read the answer from the editor log:
#   grep -E "LogMetaHumanAuth|Auto-Rigging|texture sources|not logged in" /project/ue/logs/metahuman/editor.log
# Observed 2026-11-23: "Login failed - error code: EOS_InvalidAuth", "Auto-Rigging of Face failed with code
# 'Login Failed'", "User not logged in, please autorig before downloading source face textures".
import unreal

sub = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = unreal.load_asset(globals().get("MH_PATH", "/Game/MH/MH_Probe"))
if not sub.is_object_added_for_editing(ch):
    sub.try_add_object_to_edit(ch)
p = unreal.MetaHumanCharacterAutoRiggingRequestParams()
p.blocking = False
p.report_progress = False
p.rig_type = unreal.MetaHumanRigType.JOINTS_ONLY
sub.request_auto_rigging(ch, p)
t = unreal.MetaHumanCharacterTextureRequestParams()
t.blocking = False
t.report_progress = False
sub.request_texture_sources(ch, t)
"requested (read the editor log)"
