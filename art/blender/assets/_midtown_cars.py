"""Midtown round 3: the parked cars (14 colliders of sedan, taxi, SUV and van on Seventh Av, Broadway and W 46 St).

The Block's four vehicles are 168k to 178k triangles each (the gun-range cars of the first map); five of them in a view would
put a million triangles on screen. Here each is collapsed once to a light Midtown version (same slots, size and pivot, the
cabin kept as the glass shows it) and once more to a LOD1 drawn past 12 m. Collision is the level data's two boxes per car
(the body and the glass) and is not on the art.
"""
import os

# Block mesh -> (Midtown mesh, LOD0 triangles, LOD1 triangles)
CARS = {"SM_Vehicle_Sedan": ("SM_Vehicle_MT_Sedan", 14000, 3600), "SM_Vehicle_Taxi": ("SM_Vehicle_MT_Taxi", 14000, 3600),
        "SM_Vehicle_SUV": ("SM_Vehicle_MT_SUV", 15000, 3900), "SM_Vehicle_Van": ("SM_Vehicle_MT_Van", 14000, 3600)}


def build(ctx):
    """The light cars and their LOD1s, into ctx.K (and ctx.assets, notes only: the materials are the Block's)."""
    import bpy
    from assets import _chinatown_lod as cl
    from mi import paths
    man = cl._manifest()
    for src_name, (name, t0, t1) in CARS.items():
        rec = man[src_name]
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=os.path.join(paths.out, rec["glb"]))
        new = [o for o in bpy.data.objects if o not in before]
        meshes = [o for o in new if o.type == "MESH"]
        for o in new:
            if o.type != "MESH":
                bpy.data.objects.remove(o)
        assert len(meshes) == 1, (src_name, len(meshes))
        src = meshes[0]
        for nm, target in ((name, t0), (name + "_LOD1", t1)):
            ob = bpy.data.objects.new(nm, src.data.copy())
            ob.data.name = nm
            ctx.kit.objects.link(ob)
            ob.matrix_world = src.matrix_world.copy()
            cl._base_materials(ob)
            cl._collapse(ob, target)
            cl._base_materials(ob)
            note = ("The Block's %s collapsed to about %.1fk triangles (same size, slots and pivot) for the parked cars on the avenues; "
                    "collision is the level data's body and glass boxes." % (src_name, target / 1000.0)) if nm == name else \
                   "LOD1 of %s (about %.1fk triangles), drawn past 12 m; same slots." % (name, target / 1000.0)
            ctx.asset(ob, collision="none", notes=note)
            ctx.K[nm] = ob
        bpy.data.objects.remove(src)
