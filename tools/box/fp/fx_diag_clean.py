"""Removes the cards fx_diag.py put in the level (actors tagged MIDiag)."""
import unreal

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
N = 0
for a in EAS.get_all_level_actors():
    if a.actor_has_tag("MIDiag"):
        EAS.destroy_actor(a)
        N += 1
N
