"""Converged still picture from a fixed camera, taken inside the running editor (used by tools/box/shot.sh).

The MCP capture tool renders one frame without temporal history, so Lumen lighting, the real-time sky light and
temporal anti-aliasing have not settled: shadows come out black. This module renders the same view once per editor
tick for a number of frames through a scene capture that keeps its rendering state, then writes the last frame.

    import mi_shot
    mi_shot.start("/tmp/shot.png", (x, y, z), (pitch, yaw, roll), fov=90, width=1920, height=1080, frames=24)

start() returns at once. When the picture is written, "<out>.done" appears next to it holding "OK" or an error text.
"""
import os
import traceback

import unreal

_JOBS = []


class _Job:
    def __init__(self, out_png, location, rotation, fov, width, height, frames, game):
        self.out_png = out_png
        self.frames_left = max(1, int(frames))
        editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        self.world = (editor.get_game_world() if game else None) or editor.get_editor_world()
        self.target = unreal.RenderingLibrary.create_render_target2d(
            self.world, int(width), int(height), unreal.TextureRenderTargetFormat.RTF_RGBA8)
        transform = unreal.Transform(
            unreal.Vector(*location), unreal.Rotator(roll=rotation[2], pitch=rotation[0], yaw=rotation[1]))
        # Spawned straight into the world (not through the editor's actor subsystem): no undo record, and removed again.
        self.actor = unreal.GameplayStatics.finish_spawning_actor(
            unreal.GameplayStatics.begin_deferred_actor_spawn_from_class(self.world, unreal.SceneCapture2D, transform),
            transform)
        component = self.actor.capture_component2d
        component.set_editor_property("texture_target", self.target)
        component.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        component.set_editor_property("fov_angle", float(fov))
        component.set_editor_property("capture_every_frame", False)
        component.set_editor_property("capture_on_movement", False)
        component.set_editor_property("always_persist_rendering_state", True)
        component.set_editor_property("use_ray_tracing_if_enabled", True)
        self.component = component
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def finish(self, text):
        unreal.unregister_slate_post_tick_callback(self.handle)
        try:
            self.actor.destroy_actor()
        except Exception:  # noqa: BLE001 - the world may already be gone (play-in-editor stopped)
            pass
        with open(self.out_png + ".done", "w", encoding="utf-8") as handle:
            handle.write(text)
        if self in _JOBS:
            _JOBS.remove(self)

    def tick(self, delta_seconds):
        try:
            self.component.capture_scene()
            self.frames_left -= 1
            if self.frames_left > 0:
                return
            directory, name = os.path.split(self.out_png)
            unreal.RenderingLibrary.export_render_target(self.world, self.target, directory, name)
            self.finish("OK" if os.path.exists(self.out_png) else "export_render_target wrote no file")
        except Exception:  # noqa: BLE001 - report every failure through the .done file
            self.finish("ERROR " + traceback.format_exc()[-600:])


def start(out_png, location, rotation, fov=90.0, width=1920, height=1080, frames=24, game=True):
    """game=True uses the play-in-editor world when one is running, else the editor world."""
    for path in (out_png, out_png + ".done"):
        if os.path.exists(path):
            os.remove(path)
    _JOBS.append(_Job(out_png, location, rotation, fov, width, height, frames, game))
    return "started: %d frames to %s" % (frames, out_png)
