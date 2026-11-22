#!/usr/bin/env python3
"""Probe candidate Poly Haven slugs on the download host (HEAD only, never the API).

Usage:
    python3 art/scans/probe.py textures|hdris|models slug ...
    python3 art/scans/probe.py path Textures/gltf/2k/asphalt_02/asphalt_02_2k.gltf ...
    python3 art/scans/probe.py --status

Every answer is remembered in art/scans/probes.json, so a slug is never asked about twice and the number of
requests that went out stays visible. The host is a donation-funded CDN: at most 4 requests at a time, and the
tool refuses to go past its budget (300 probes for the session that built this library).
"""
import concurrent.futures as cf
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://dl.polyhaven.org/file/ph-assets"
UA = {"User-Agent": "asset-pipeline/1.0"}
LOG = Path(__file__).resolve().parent / "probes.json"
BUDGET = 300
KINDS = ("textures", "hdris", "models", "path")


def path_for(kind, slug):
    """The one file whose existence stands for the whole asset."""
    if kind == "textures":
        return f"Textures/jpg/2k/{slug}/{slug}_diff_2k.jpg"
    if kind == "hdris":
        return f"HDRIs/hdr/2k/{slug}_2k.hdr"
    if kind == "models":
        return f"Models/gltf/2k/{slug}/{slug}_2k.gltf"
    return slug  # kind == "path": the argument is already a path under BASE


def load():
    if LOG.exists():
        return json.loads(LOG.read_text())
    return {"budget": BUDGET, "sent": 0, "textures": {}, "hdris": {}, "models": {}, "path": {}}


def save(log):
    LOG.write_text(json.dumps(log, indent=1, sort_keys=True) + "\n")


def head(kind, slug):
    req = urllib.request.Request(f"{BASE}/{path_for(kind, slug)}", method="HEAD", headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return slug, r.status, int(r.headers.get("Content-Length") or 0)
    except urllib.error.HTTPError as e:
        return slug, e.code, 0
    except Exception as e:  # network trouble: not an answer, do not record it
        return slug, f"error: {str(e)[:60]}", 0


def main(argv):
    log = load()
    if not argv or argv[0] == "--status":
        for kind in KINDS:
            ok = sorted(s for s, v in log[kind].items() if v["status"] == 200)
            bad = sorted(s for s, v in log[kind].items() if v["status"] != 200)
            print(f"{kind}: {len(ok)} found, {len(bad)} missing")
            print("  found:  ", " ".join(ok))
            print("  missing:", " ".join(bad))
        print(f"probes sent by this tool: {log['sent']} of {log['budget']}")
        return 0
    kind, slugs = argv[0], list(dict.fromkeys(argv[1:]))
    if kind not in KINDS:
        print(__doc__)
        return 2
    todo = [s for s in slugs if s not in log[kind]]
    left = log["budget"] - log["sent"]
    if len(todo) > left:
        print(f"refusing: {len(todo)} new probes asked, {left} left in the budget")
        return 1
    if todo:
        with cf.ThreadPoolExecutor(4) as ex:
            for slug, status, size in ex.map(lambda s: head(kind, s), todo):
                log["sent"] += 1
                if isinstance(status, int):
                    log[kind][slug] = {"status": status, "bytes": size, "via": "probe"}
                else:
                    print(f"{slug}: {status} (not recorded)")
        save(log)
    known = [s for s in slugs if s in log[kind]]
    print(kind, "OK:", " ".join(s for s in known if log[kind][s]["status"] == 200))
    print(kind, "missing:", " ".join(s for s in known if log[kind][s]["status"] != 200))
    print(f"({len(todo)} new, {len(slugs) - len(todo)} answered from probes.json; {log['sent']} of {log['budget']} sent)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
