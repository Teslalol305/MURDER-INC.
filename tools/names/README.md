# tools/names: the approved sign and screen names for Levels 2 and 3 (MAPS.md lane C)

Pure Python 3; no Blender, no Unreal, nothing the game loads.

```
python3 tools/names/build_names.py   # the tables (every name, its web search, the finding, the verdict) -> names.json
python3 tools/names/check_names.py   # the art lists, layouts, level files and designs against names.json (exit 1 on a FAIL)
```

| File | What |
|---|---|
| `build_names.py` | The source: every invented business, product, show and building name on Canal Street and Midtown, the query as run on 2026-11-26, what it found, and `approved`, `retired` or `replaces <old>` |
| `names.json` | Written by `build_names.py`: the approved list, the retired names with their replacements, the generic words, the real places, the story marks, `signedOff` (null until the owner signs) |
| `check_names.py` | 1. no retired name left (text or id) in the files of its `SCAN` list; 2. every name an art list's `business_names()` reports is approved, generic, a real place or a story mark; 3. no CJK character in those files |

The approved list for people to read, with the method, the tone review and the hand-off, is
[docs/unreal/maps/names.md](../../docs/unreal/maps/names.md).

**Adding or changing a name:** search it (the name in quotes, its trade, "New York"), add a row to `build_names.py`
with the query and what it found, run both scripts, and update names.md's tables (they are the same rows).
