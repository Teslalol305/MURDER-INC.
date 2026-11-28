#!/usr/bin/env python3
"""Offline tests for the Canal Street and Midtown level data (no engine, no box).

Rebuilds both level files from their layouts into a temp folder, checks that the committed files are byte-identical to the
rebuild, runs check_level.py (every gate must pass or be waived on record) and tools/names/check_names.py, and asserts the
data contract of docs/unreal/maps/data_contract.md (new sections and types, no drone data).
Run: python3 tools/levels/test_levels.py
"""
import json, os, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
LEVELS = ("chinatown", "midtown")
BLOCK_NEW = {"nav", "guide", "drops", "tuning", "checks", "colliderBudget", "propPlacements"}
LOADER = {"meta", "bounds", "zones", "places", "ground", "playerStart", "objectives", "extraction", "enemySpawns",
          "coverPoints", "explosives", "interior", "vantage", "cinematicPath", "steam", "puddles", "buildings", "physics",
          "colliders", "orientedBoxes", "signage", "layout"}
ABSENT = {"el", "train", "glazing", "facades"}


def run(*args):
    return subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True)


def load(path):
    with open(path) as f:
        return json.load(f)


class Levels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        r = run("tools/levels/build_level.py", "--out", cls.tmp.name)
        assert r.returncode == 0, r.stdout + r.stderr
        cls.built = {l: os.path.join(cls.tmp.name, "level_%s.json" % l) for l in LEVELS}
        cls.docs = {l: load(cls.built[l]) for l in LEVELS}

    def test_rebuild_matches_committed(self):
        for l in LEVELS:
            with open(self.built[l], "rb") as a, open(os.path.join(HERE, "data", "level_%s.json" % l), "rb") as b:
                self.assertEqual(a.read(), b.read(), "%s: committed file differs from a rebuild (run build_level.py)" % l)

    def test_checker_passes(self):
        r = run("tools/levels/check_level.py")
        self.assertEqual(r.returncode, 0, r.stdout[-3000:] + r.stderr[-1000:])
        self.assertNotIn("FAIL", [ln.split()[0] for ln in r.stdout.splitlines() if ln.strip()])

    def test_names_clean(self):
        r = run("tools/names/check_names.py")
        self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-500:])

    def test_contract_sections(self):
        for l, d in self.docs.items():
            self.assertTrue(LOADER <= set(d), "%s missing %s" % (l, LOADER - set(d)))
            self.assertTrue(BLOCK_NEW <= set(d), "%s missing %s" % (l, BLOCK_NEW - set(d)))
            self.assertFalse(ABSENT & set(d), "%s has %s" % (l, ABSENT & set(d)))
            nav = d["nav"]
            self.assertIsNone(None if all(x["grid"] is None for x in nav["layers"]) else 1, "grids are the bake's")
            ids = [x["id"] for x in nav["layers"]]
            self.assertEqual(len(ids), len(set(ids)))
            for x in nav["layers"]:
                self.assertIn(x["floor"], ("plane", "boxes"))
                self.assertTrue({"y", "rect", "cols", "rows"} <= set(x))
            for k in nav["links"]:
                self.assertTrue(k["a"] in ids and k["b"] in ids and len(k["path"]) >= 2)
            self.assertTrue(set(nav["spawnReach"]) <= set(ids))
            g = d["guide"]
            self.assertEqual(g["mode"], "routeGraph")
            n = len(g["graph"]["nodes"])
            for e in g["graph"]["edges"]:
                self.assertTrue(0 <= e["from"] < n and 0 <= e["to"] < n)
                self.assertIn(e["kind"], ("stair", "drop"))
                self.assertEqual(e["kind"] == "drop", bool(e.get("oneWay")))
            for p in d["enemySpawns"]["points"]:
                self.assertIn(p["layer"] if p["type"] == "ground" else "street", ids)
            for o in d["objectives"]:
                self.assertIn(o["layer"], ids)
            for dr in d["drops"]["items"]:
                self.assertLess(dr["height"] + 1.0, 4.02)
            for k in d["tuning"]:
                self.assertIn(k, ("source", "difficulty", "spawn", "rating", "startPitch"))

    def test_no_drone_data(self):
        for l, d in self.docs.items():
            self.assertFalse([p for p in d["enemySpawns"]["points"] if p["type"] != "ground"], l + " has air points")
            self.assertEqual(d["interior"]["doorways"], [], l + " has doorways")
            self.assertEqual(d["meta"]["counts"]["enemySpawns"]["air"], 0)
            t = d["tuning"]
            self.assertNotIn("buzzard", t)
            self.assertNotIn("waveAdd", t.get("difficulty", {}))
            self.assertNotIn("waveAddOn", t.get("difficulty", {}))

    def test_midtown_truck_arrives_late(self):
        d = self.docs["midtown"]
        self.assertEqual(d["extraction"]["arrival"], "afterAll")
        for i in d["extraction"]["truck"]["colliders"]:
            self.assertEqual(d["colliders"]["boxes"][i]["owner"]["kind"], "truck")

    def test_canal_roof_spawns_enabled(self):
        # Nav step A keeps Goons on their own layer: the roof spawns are on, so a roof player is fought (RoofCamp).
        pts = self.docs["chinatown"]["enemySpawns"]["points"]
        self.assertEqual([p["name"] for p in pts if p.get("enabled") is False], [])
        roof = [p for p in pts if p["layer"] == "roof"]
        self.assertEqual(sorted(p["name"] for p in roof), ["rf1", "rf2", "rf3"])
        self.assertTrue(all(p.get("enabled", True) and p.get("overlooks") for p in roof))


if __name__ == "__main__":
    unittest.main(verbosity=2)
