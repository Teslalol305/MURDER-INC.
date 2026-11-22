"""mi: the MURDER INC. Blender art library.

    import sys; sys.path.insert(0, "art/blender")
    from mi import scene, geo, mat, bake, export, render

Everything is metres, Z up, east = +X, north = +Y (see art/blender/README.md for the shared conventions).
The modules only depend on bpy, bmesh, mathutils, numpy and (for JPEG/PNG packing) pillow.
"""
import os

__all__ = ["scene", "geo", "mat", "bake", "export", "render", "paths"]

# art/ directory (this file is art/blender/mi/__init__.py)
ART_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
REPO_DIR = os.path.dirname(ART_DIR)


class paths:
    """Where things go. Generated output is git-ignored (art/out), previews are committed."""
    art = ART_DIR
    out = os.path.join(ART_DIR, "out")
    blend = os.path.join(ART_DIR, "out", "blend")
    glb = os.path.join(ART_DIR, "out", "glb")
    fbx = os.path.join(ART_DIR, "out", "fbx")
    textures = os.path.join(ART_DIR, "out", "textures")
    manifest = os.path.join(ART_DIR, "out", "manifest.json")
    previews = os.path.join(ART_DIR, "previews")

    @staticmethod
    def texture_set(set_name):
        return os.path.join(paths.textures, set_name)

    @staticmethod
    def ensure(*dirs):
        for d in dirs:
            os.makedirs(d, exist_ok=True)
        return dirs[0] if dirs else None
