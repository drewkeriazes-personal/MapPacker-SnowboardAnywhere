"""FEAT-243: the hand content that moved from the game into resorts/<slug>/ is in shape."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import paths  # noqa: E402
from pack_report import nearest_run  # noqa: E402


def _load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def test_vail_has_its_gateway_as_start():
    lm = _load(paths.landmarks_path("vail"))
    assert len(lm) == 1
    g = lm[0]
    assert g["id"] == "back-bowls-gateway" and g["start"] is True
    assert (g["x"], g["y"], g["heading"]) == (-718.0, 495.9, 162)
    assert g["note"]


def test_breckenridge_start():
    s = _load(paths.start_path("breckenridge"))
    assert (s["x"], s["y"], s["heading"]) == (-1670, -268, 155)
    assert s["label"] == "Starts at the top of Imperial Bowl" and s["source"] and s["note"]


# Imperial Bowl's area in the breckenridge v4 pack (build 20261114T151850Z-9cb882, features.json, rounded)
IMPERIAL_BOWL = [[-1677, -258], [-1690, -332], [-1680, -360], [-1661, -385], [-1641, -415], [-1599, -459],
                 [-1518, -526], [-1458, -551], [-1328, -579], [-1240, -620], [-1175, -638], [-1128, -646],
                 [-1078, -566], [-1042, -480], [-1013, -392], [-1006, -356], [-1063, -264], [-1099, -238],
                 [-1151, -229], [-1293, -223], [-1429, -208], [-1564, -216], [-1629, -223], [-1677, -258]]


def test_the_breckenridge_start_is_in_imperial_bowl():
    s = _load(paths.start_path("breckenridge"))     # BUG-132: on a run, so line 10 passes
    off, name = nearest_run([{"name": "Imperial Bowl", "area": True, "points": IMPERIAL_BOWL}], s["x"], s["y"])
    assert (off, name) == (0.0, "Imperial Bowl")
