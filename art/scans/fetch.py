#!/usr/bin/env python3
"""Fetch the scanned surface, sky and prop library listed in sets.json and lay it out in the project conventions.

    python3 art/scans/fetch.py [--res 2k|4k] [--only set ...] [--offline] [--quiet]

What it does, in order:
  1. reads art/scans/sets.json (the catalogue: nothing is downloaded that is not listed there);
  2. downloads every listed file from Poly Haven's download host into art/out/scans/raw/ (a mirror of the remote
     paths), at most 4 at a time, never asking for a file that is already there or that already answered 404;
  3. writes the convention files:
        art/out/textures/<Set>/T_<Set>_BC.jpg   sRGB base colour            (source JPEG bytes, untouched)
        art/out/textures/<Set>/T_<Set>_N.jpg    tangent-space normal, OpenGL (source JPEG bytes, untouched)
        art/out/textures/<Set>/T_<Set>_ORM.jpg  R = AO, G = roughness, B = metallic, linear
                                                (the source _arm JPEG as it is, or packed here from separate maps)
        art/out/textures/<Set>/T_<Set>_H.png    height, 16-bit                (source PNG bytes, untouched)
        art/out/hdri/<slug>_<res>.hdr
        art/out/scans/models/<slug>/...         exactly as downloaded (.gltf, .bin, textures/*.jpg: the layout
                                                the .gltf itself refers to, so it opens as it is)
  4. verifies that every image opens and has the size the catalogue promises, that every glTF buffer is complete;
  5. prints a table and exits non-zero if anything is missing or wrong.

Standard library, pillow and numpy only. Running it again does no network traffic and rewrites nothing.
All assets are CC0 (Poly Haven). Direct file URLs only: this script never talks to the Poly Haven API.
"""
import argparse
import concurrent.futures as cf
import json
import os
import shutil
import struct
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ART = HERE.parent
OUT = ART / "out"
RAW = OUT / "scans" / "raw"
CATALOGUE = HERE / "sets.json"
BASE = "https://dl.polyhaven.org/file/ph-assets"
USER_AGENT = "asset-pipeline/1.0"
MAX_PARALLEL = 4
RES_PX = {"1k": 1024, "2k": 2048, "4k": 4096, "8k": 8192}


# ----------------------------------------------------------------------------------------------- download cache

class Cache:
    """A mirror of the remote tree under art/out/scans/raw/. One request per file, ever."""

    def __init__(self, root=RAW, offline=False):
        self.root = Path(root)
        self.offline = offline
        self.lock = threading.Lock()
        self.missing_file = self.root / "missing.json"
        self.missing = json.loads(self.missing_file.read_text()) if self.missing_file.exists() else {}
        self.fetched = []  # (remote path, bytes) downloaded during this run

    def path(self, rel):
        return self.root / rel

    def has(self, rel):
        return self.path(rel).is_file()

    def _note_missing(self, rel, status):
        with self.lock:
            self.missing[rel] = status
            self.root.mkdir(parents=True, exist_ok=True)
            tmp = self.missing_file.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.missing, indent=1, sort_keys=True) + "\n")
            os.replace(tmp, self.missing_file)

    def get(self, rel):
        """Local path of a remote file, downloading it once. None when the host does not have it."""
        dest = self.path(rel)
        if dest.is_file():
            return dest
        if rel in self.missing or self.offline:
            return None
        url = f"{BASE}/{urllib.parse.quote(rel)}"
        part = dest.with_name(dest.name + ".part")
        last = None
        for attempt in range(4):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=120) as r:
                    want = int(r.headers.get("Content-Length") or 0)
                    dest.parent.mkdir(parents=True, exist_ok=True)  # only once the host has said yes
                    with open(part, "wb") as f:
                        shutil.copyfileobj(r, f, 1 << 20)
                got = part.stat().st_size
                if want and got != want:
                    raise IOError(f"short read: {got} of {want} bytes")
                os.replace(part, dest)
                with self.lock:
                    self.fetched.append((rel, got))
                return dest
            except urllib.error.HTTPError as e:
                if e.code in (403, 404, 410):  # an answer, not a failure: remember it and never ask again
                    self._note_missing(rel, e.code)
                    return None
                last = e
            except Exception as e:  # timeouts, resets: try again, slowly
                last = e
            time.sleep(3 * (attempt + 1))
        if part.exists():
            part.unlink()
        raise IOError(f"could not download {rel}: {last}")

    def get_many(self, rels):
        """Download a batch, at most MAX_PARALLEL at a time. Returns {rel: path or None}."""
        rels = list(dict.fromkeys(rels))
        with cf.ThreadPoolExecutor(MAX_PARALLEL) as ex:
            return dict(zip(rels, ex.map(self.get, rels)))


# ------------------------------------------------------------------------------------------------- file readers

def image_info(path):
    """(width, height, mode) of an image, after really decoding it."""
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    with Image.open(path) as im:
        im.load()
        return im.size[0], im.size[1], im.mode


def hdr_header(path):
    """(width, height) of a Radiance .hdr, checking the magic, the format line and the first scanline marker."""
    with open(path, "rb") as f:
        head = f.read(4096)
    if not head.startswith(b"#?RADIANCE") and not head.startswith(b"#?RGBE"):
        raise ValueError("not a Radiance HDR file")
    end = head.find(b"\n\n")
    if end < 0 or b"FORMAT=32-bit_rle_rgbe" not in head[:end]:
        raise ValueError("unexpected HDR header")
    line = head[end + 2:head.find(b"\n", end + 2)].split()
    if len(line) != 4 or line[0] != b"-Y" or line[2] != b"+X":
        raise ValueError(f"unexpected HDR orientation {line}")
    return int(line[3]), int(line[1])


def read_hdr(path):
    """Decode a Radiance .hdr into a float32 array (height, width, 3), linear, top row first."""
    import numpy as np
    data = Path(path).read_bytes()
    w, h = hdr_header(path)
    end = data.find(b"\n\n")
    pos = data.find(b"\n", end + 2) + 1
    rgbe = np.empty((h, w, 4), np.uint8)
    if not (8 <= w < 32768) or data[pos] != 2 or data[pos + 1] != 2:  # flat, not run-length encoded
        rgbe[:] = np.frombuffer(data, np.uint8, h * w * 4, pos).reshape(h, w, 4)
    else:
        for y in range(h):
            if data[pos] != 2 or data[pos + 1] != 2 or (data[pos + 2] << 8 | data[pos + 3]) != w:
                raise ValueError(f"bad scanline {y}")
            pos += 4
            for c in range(4):
                row = bytearray()
                while len(row) < w:
                    n = data[pos]
                    if n > 128:  # a run
                        row += data[pos + 1:pos + 2] * (n - 128)
                        pos += 2
                    else:  # literal bytes
                        row += data[pos + 1:pos + 1 + n]
                        pos += 1 + n
                if len(row) != w:
                    raise ValueError(f"scanline {y} overruns")
                rgbe[y, :, c] = np.frombuffer(bytes(row), np.uint8)
    scale = np.ldexp(1.0, rgbe[..., 3].astype(np.int32) - 136).astype(np.float32)
    scale[rgbe[..., 3] == 0] = 0.0
    return rgbe[..., :3].astype(np.float32) * scale[..., None]


def png_header(path):
    """(width, height, bit depth, channels) straight from the IHDR chunk."""
    with open(path, "rb") as f:
        head = f.read(33)
    if head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        raise ValueError("not a PNG")
    w, h, depth, ctype = struct.unpack(">IIBB", head[16:26])
    return w, h, depth, {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]


def read_png(path):
    """Decode a non-interlaced 8- or 16-bit PNG at full depth: (height, width, channels), uint8 or uint16.

    Pillow keeps 16 bits only for plain greyscale; a 16-bit grey+alpha or RGB file comes back with 8 bits per
    channel, which would throw away most of a height map. The filters make every byte depend on its left, upper
    and upper-left neighbours, so the bytes on one anti-diagonal are independent of each other: the picture is
    rebuilt one anti-diagonal at a time, each as a single numpy operation.
    """
    import numpy as np
    data = Path(path).read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    pos, idat, ihdr = 8, [], None
    while pos < len(data):
        n, kind = struct.unpack(">I4s", data[pos:pos + 8])
        if kind == b"IHDR":
            ihdr = struct.unpack(">IIBBBBB", data[pos + 8:pos + 8 + n])
        elif kind == b"IDAT":
            idat.append(data[pos + 8:pos + 8 + n])
        elif kind == b"IEND":
            break
        pos += 12 + n
    w, h, depth, ctype, _, _, interlace = ihdr
    if interlace or depth not in (8, 16) or ctype not in (0, 2, 4, 6):
        raise ValueError(f"unsupported PNG (depth {depth}, colour type {ctype}, interlace {interlace})")
    channels = {0: 1, 2: 3, 4: 2, 6: 4}[ctype]
    bpp = channels * depth // 8
    raw = np.frombuffer(zlib.decompress(b"".join(idat)), np.uint8).reshape(h, 1 + w * bpp)
    kind = raw[:, 0].astype(np.int16)
    filt = raw[:, 1:].reshape(h, w, bpp).astype(np.int16)
    rec = np.zeros((h + 1, w + 1, bpp), np.int16)  # row 0 and column 0 are the zeros the filters assume
    for t in range(w + h - 1):
        ys = np.arange(max(0, t - w + 1), min(h - 1, t) + 1)
        xs = t - ys
        k = kind[ys][:, None]
        a, b, c = rec[ys + 1, xs], rec[ys, xs + 1], rec[ys, xs]  # left, up, upper left
        p = a + b - c
        pa, pb, pc = np.abs(p - a), np.abs(p - b), np.abs(p - c)
        paeth = np.where((pa <= pb) & (pa <= pc), a, np.where(pb <= pc, b, c))
        pred = np.where(k == 1, a, np.where(k == 2, b, np.where(k == 3, (a + b) >> 1, np.where(k == 4, paeth, 0))))
        rec[ys + 1, xs + 1] = (filt[ys, xs] + pred) & 255
    out = rec[1:, 1:].astype(np.uint8)
    if depth == 8:
        return out.reshape(h, w, channels)
    out = out.reshape(h, w, channels, 2).astype(np.uint16)
    return (out[..., 0] << 8) | out[..., 1]


def write_grey(height, dest):
    """Save a uint8 or uint16 array as a greyscale PNG of the same depth."""
    from PIL import Image
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".tmp")
    Image.fromarray(height).save(tmp, "PNG", optimize=False, compress_level=6)
    os.replace(tmp, dest)


def power_of_two(v):
    """The power of two nearest to v (ties go up)."""
    lo = 1 << (max(1, int(v)).bit_length() - 1)
    return lo if v - lo < lo * 2 - v else lo * 2


def resample(src, dest, size, role):
    """Re-encode one map at `size`: for the few scans that are a handful of pixels off square (a game engine
    wants powers of two for mip-mapping and streaming). The picture is squeezed, not cropped, so it still tiles;
    the tile keeps its size in metres."""
    import numpy as np
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".tmp")
    if role == "H":
        arr = read_png(src)[..., 0]
        full = 65535.0 if arr.dtype == np.uint16 else 255.0
        f = Image.fromarray(arr.astype(np.float32)).resize(size, Image.LANCZOS)
        out = np.clip(np.rint(np.asarray(f)), 0, full).astype(arr.dtype)
        Image.fromarray(out).save(tmp, "PNG", compress_level=6)
    else:
        im = Image.open(src).convert("RGB").resize(size, Image.LANCZOS)
        im.save(tmp, "JPEG", quality=95, subsampling=0, optimize=True)
    os.replace(tmp, dest)


def gltf_files(gltf_path):
    """Relative URIs a .gltf needs beside it (buffers first, then images)."""
    doc = json.loads(Path(gltf_path).read_text())
    uris = [b["uri"] for b in doc.get("buffers", []) if "uri" in b and not b["uri"].startswith("data:")]
    uris += [i["uri"] for i in doc.get("images", []) if "uri" in i and not i["uri"].startswith("data:")]
    return doc, list(dict.fromkeys(urllib.parse.unquote(u) for u in uris))


def model_part(gltf_rel, uri):
    """Remote path of a file a model's .gltf refers to.

    The buffer sits beside the .gltf. The textures do not, although the .gltf says "textures/<file>": the host
    keeps them by format and resolution, Models/<jpg|png>/<res>/<slug>/<file>.
    """
    kind, res, slug = gltf_rel.split("/")[1:4]
    if uri.startswith("textures/"):
        name = uri.split("/", 1)[1]
        return f"Models/{name.rsplit('.', 1)[-1].lower()}/{res}/{slug}/{name}"
    return f"Models/{kind}/{res}/{slug}/{uri}"


# -------------------------------------------------------------------------------------------- catalogue helpers

def remote(template, res):
    return template.replace("{res}", res)


def texture_sources(entry, res):
    """{role: remote path} for every source file a texture set lists."""
    srcs = {}
    for role, spec in entry["files"].items():
        if "src" in spec:
            srcs[role] = remote(spec["src"], res)
        for chan, tmpl in (spec.get("pack") or {}).items():
            if tmpl:
                srcs[f"{role}.{chan}"] = remote(tmpl, res)
    return srcs


def out_path(entry, role, res):
    return OUT / remote(entry["files"][role]["out"], res)


def copy_if_changed(src, dest):
    """Byte copy that leaves an identical destination alone. Returns True when it wrote."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size == src.stat().st_size and dest.stat().st_mtime >= src.stat().st_mtime:
        return False
    tmp = dest.with_name(dest.name + ".tmp")
    shutil.copyfile(src, tmp)
    os.replace(tmp, dest)
    return True


def stale(dest, *sources):
    """True when a derived file is missing or older than what it is made from."""
    return not dest.is_file() or any(dest.stat().st_mtime < src.stat().st_mtime for src in sources if src)


def quick_size(path):
    """(width, height) from the header only."""
    from PIL import Image
    with Image.open(path) as im:
        return im.size


def pack_orm(ao, rough, metal, dest):
    """Build T_<Set>_ORM.jpg from separate greyscale maps. A missing AO becomes white, a missing metallic black."""
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    g = Image.open(rough).convert("L")
    r = Image.open(ao).convert("L") if ao else Image.new("L", g.size, 255)
    b = Image.open(metal).convert("L") if metal else Image.new("L", g.size, 0)
    if r.size != g.size:
        r = r.resize(g.size, Image.LANCZOS)
    if b.size != g.size:
        b = b.resize(g.size, Image.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".tmp")
    # 4:4:4, because the three channels are unrelated data and chroma subsampling would smear them into each other
    Image.merge("RGB", (r, g, b)).save(tmp, "JPEG", quality=95, subsampling=0, optimize=True)
    os.replace(tmp, dest)


# ---------------------------------------------------------------------------------------------------- the work

def do_texture(entry, res, cache):
    """Convention files for one tiling set. Returns a table row."""
    row = {"set": entry["set"], "slug": entry["slug"], "kind": "texture", "problems": [], "wrote": 0, "bytes": 0}
    srcs = texture_sources(entry, res)
    local = {role: cache.path(rel) if cache.has(rel) else None for role, rel in srcs.items()}
    sizes = {}
    maps = []
    target = None  # set when the source is not a power of two on both sides
    if local.get("BC"):
        from PIL import Image
        with Image.open(local["BC"]) as im:
            src_size = im.size
        pot = (power_of_two(src_size[0]), power_of_two(src_size[1]))
        if pot != src_size:
            target = pot
            row["resampled"] = f"{src_size[0]}x{src_size[1]}"
    for role, spec in entry["files"].items():
        dest = out_path(entry, role, res)
        if target and "src" in spec and local.get(role):
            if stale(dest, local[role]) or quick_size(dest) != target:
                resample(local[role], dest, target, role)
                row["wrote"] += 1
        elif role == "H" and local.get(role) and png_header(local[role])[3] != 1:
            # the source PNG carries the height in RGB or grey+alpha: keep channel 0 at its full depth
            if stale(dest, local[role]) or png_header(dest)[3] != 1:
                write_grey(read_png(local[role])[..., 0], dest)
                row["wrote"] += 1
        elif "src" in spec and local.get(role):
            row["wrote"] += copy_if_changed(local[role], dest)
        elif spec.get("pack") and local.get(f"{role}.rough"):
            parts = [local.get(f"{role}.{c}") for c in ("ao", "rough", "metal")]
            if stale(dest, *parts):
                pack_orm(*parts, dest)
                row["wrote"] += 1
        else:
            row["problems"].append(f"{role}: source missing")
            continue
        try:
            w, h, mode = image_info(dest)
        except Exception as e:
            row["problems"].append(f"{role}: does not open ({e})")
            continue
        sizes[role] = (w, h)
        row["bytes"] += dest.stat().st_size
        tag = role
        if role == "ORM":
            tag += "(packed)" if spec.get("pack") and "src" not in spec else ""
        if role == "H":
            _, _, depth, channels = png_header(dest)
            tag += str(depth)
            if channels != 1:
                row["problems"].append(f"H has {channels} channels, expected a single grey channel")
        maps.append(tag)
        if role == "BC" and mode != "RGB":
            row["problems"].append(f"BC is {mode}, expected RGB")
    want = RES_PX[res]
    scale = want / RES_PX[entry.get("resolution", "2k")]
    expect = tuple(round(v * scale) for v in entry["px"]) if entry.get("px") else None
    for role, size in sizes.items():
        if size[0] != want:
            row["problems"].append(f"{role}: {size[0]}x{size[1]}, width should be {want}")
        if size[0] & (size[0] - 1) or size[1] & (size[1] - 1):
            row["problems"].append(f"{role}: {size[0]}x{size[1]} is not a power of two")
        if expect and size != expect:
            row["problems"].append(f"{role}: {size[0]}x{size[1]}, catalogue says {expect[0]}x{expect[1]}")
    if len(set(sizes.values())) > 1:
        row["problems"].append(f"maps differ in size: {sizes}")
    size = sizes.get("BC") or (next(iter(sizes.values())) if sizes else None)
    row["px"] = f"{size[0]}x{size[1]}" if size else "-"
    tile = entry.get("tile_m")
    row["tile"] = f"{tile[0]:.2f} x {tile[1]:.2f}" if tile else "-"
    row["density"] = f"{size[0] / tile[0]:.0f}" if size and tile else "-"
    row["maps"] = " ".join(maps) + (" (resampled)" if target else "")
    return row


def do_hdri(entry, res, cache):
    row = {"set": entry["set"], "slug": entry["slug"], "kind": "hdri", "problems": [], "wrote": 0, "bytes": 0,
           "tile": "-", "density": "-", "px": "-", "maps": "hdr"}
    spec = entry["files"]["HDR"]
    src = cache.path(remote(spec["src"], res))
    dest = OUT / remote(spec["out"], res)
    if not src.is_file():
        row["problems"].append("source missing")
        return row
    row["wrote"] += copy_if_changed(src, dest)
    try:
        w, h = hdr_header(dest)
        row["px"] = f"{w}x{h}"
        if (w, h) != (RES_PX[res], RES_PX[res] // 2):
            row["problems"].append(f"{w}x{h}, expected {RES_PX[res]}x{RES_PX[res] // 2}")
    except Exception as e:
        row["problems"].append(f"does not open ({e})")
    row["bytes"] = dest.stat().st_size
    return row


def do_model(entry, res, cache):
    row = {"set": entry["set"], "slug": entry["slug"], "kind": "model", "problems": [], "wrote": 0, "bytes": 0,
           "tile": "-", "density": "-", "px": "-", "maps": ""}
    spec = entry["files"]["GLTF"]
    rel = remote(spec["src"], res)
    src = cache.path(rel)
    dest_dir = OUT / remote(spec["out"], res)
    if not src.is_file():
        row["problems"].append("gltf missing")
        return row
    doc, uris = gltf_files(src)
    row["wrote"] += copy_if_changed(src, dest_dir / src.name)
    row["bytes"] += src.stat().st_size
    n_img = 0
    for uri in uris:
        part = cache.path(model_part(rel, uri))
        if not part.is_file():
            row["problems"].append(f"{uri}: missing")
            continue
        row["wrote"] += copy_if_changed(part, dest_dir / uri)
        row["bytes"] += part.stat().st_size
        if uri.lower().endswith((".jpg", ".jpeg", ".png")):
            try:
                w, h, _ = image_info(dest_dir / uri)
                n_img += 1
                if max(w, h) != RES_PX[res]:
                    row["problems"].append(f"{uri}: {w}x{h}, longest side should be {RES_PX[res]}")
            except Exception as e:
                row["problems"].append(f"{uri}: does not open ({e})")
    for buf in doc.get("buffers", []):
        uri = urllib.parse.unquote(buf.get("uri", ""))
        f = dest_dir / uri
        if uri and f.is_file() and f.stat().st_size != buf["byteLength"]:
            row["problems"].append(f"{uri}: {f.stat().st_size} bytes, glTF says {buf['byteLength']}")
    want = entry.get("files", {}).get("GLTF", {}).get("parts")
    if want is not None and sorted(want) != sorted(uris):
        row["problems"].append("file list differs from the catalogue")
    dims = entry.get("measured", {}).get("size_m")
    row["tile"] = "{:.2f} x {:.2f} x {:.2f}".format(*dims) if dims else "-"
    row["px"] = f"{entry.get('measured', {}).get('triangles', '-')} tris"
    row["maps"] = f"gltf + {len(uris) - n_img} bin + {n_img} tex"
    return row


def plan_downloads(entries, res):
    """Remote files to have before any conversion (models add their parts once the .gltf is here)."""
    rels = []
    for e in entries:
        if e["kind"] == "texture":
            rels += texture_sources(e, res).values()
        elif e["kind"] == "hdri":
            rels.append(remote(e["files"]["HDR"]["src"], res))
        elif e["kind"] == "model":
            rels.append(remote(e["files"]["GLTF"]["src"], res))
    return rels


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--res", default="2k", choices=sorted(RES_PX), help="resolution to fetch (default 2k)")
    ap.add_argument("--only", nargs="+", metavar="SET", help="only these sets (TS_ name, or slug for skies and models)")
    ap.add_argument("--offline", action="store_true", help="do not touch the network, use the cache only")
    ap.add_argument("--quiet", action="store_true", help="print problems and the summary only")
    args = ap.parse_args(argv)

    cat = json.loads(CATALOGUE.read_text())
    entries = cat["sets"]
    if args.only:
        names = set(args.only)
        entries = [e for e in entries if e["set"] in names or e["slug"] in names]
        unknown = names - {e["set"] for e in entries} - {e["slug"] for e in entries}
        if unknown:
            print("not in the catalogue:", " ".join(sorted(unknown)))
            return 2
    cache = Cache(offline=args.offline)
    t0 = time.time()
    cache.get_many(plan_downloads(entries, args.res))
    parts = []
    for e in entries:
        if e["kind"] == "model":
            rel = remote(e["files"]["GLTF"]["src"], args.res)
            if cache.has(rel):
                parts += [model_part(rel, u) for u in gltf_files(cache.path(rel))[1]]
    cache.get_many(parts)

    work = {"texture": do_texture, "hdri": do_hdri, "model": do_model}
    rows = [work[e["kind"]](e, args.res, cache) for e in entries]

    if not args.quiet:
        cols = [("set", 34), ("slug", 30), ("px", 12), ("tile", 20), ("density", 7), ("maps", 24)]
        print("  ".join(name.ljust(width) for name, width in cols) + "  MB      state")
        print("  ".join("-" * width for _, width in cols) + "  ------  -----")
        for r in rows:
            state = "FAIL" if r["problems"] else ("written" if r["wrote"] else "ok")
            print("  ".join(str(r[name]).ljust(width) for name, width in cols) + f"  {r['bytes'] / 1e6:6.1f}  {state}")
        print("(tile: metres covered by one repeat, x by y; density: pixels per metre; models: bounding box and triangles)")
    bad = [r for r in rows if r["problems"]]
    for r in bad:
        for p in r["problems"]:
            print(f"PROBLEM {r['set']}: {p}")
    got = sum(b for _, b in cache.fetched)
    kinds = {k: sum(1 for r in rows if r["kind"] == k) for k in ("texture", "hdri", "model")}
    print(f"{kinds['texture']} texture sets, {kinds['hdri']} skies, {kinds['model']} models at {args.res}: "
          f"{sum(r['bytes'] for r in rows) / 1e6:.0f} MB in place, {len(cache.fetched)} files ({got / 1e6:.0f} MB) downloaded, "
          f"{sum(r['wrote'] for r in rows)} written, {len(bad)} with problems, {time.time() - t0:.0f} s")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
