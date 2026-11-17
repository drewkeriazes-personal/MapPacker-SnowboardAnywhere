"""FEAT-331: the canopy density grid (canopy.py) on a small pack: orientation, the score's references, the stems, the
meta entry, and a pack without one."""
import json, os, sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import canopy, stands  # noqa: E402

# bounds not a multiple of 10 m, so the grid rounds up (and still starts at minX, minY)
BOUNDS = {"minX": -500, "minY": -300, "maxX": 505, "maxY": 300}


def block(x0, y0, size, step, height, species=0):
    """trees on a square lattice: x, y, z, height, crown radius (species formula), species"""
    xs, ys = np.meshgrid(np.arange(x0, x0 + size, step) + step / 2, np.arange(y0, y0 + size, step) + step / 2)
    n = xs.size
    return np.stack([xs.ravel(), ys.ravel(), np.zeros(n), np.full(n, height), np.full(n, 0.13 * height),
                     np.full(n, species)], axis=1).astype(np.float32)


def make_pack(d, trees, stand=None):
    os.makedirs(os.path.join(d, "trees"), exist_ok=True)
    trees.astype("<f4").tofile(os.path.join(d, "trees", "0_0.bin"))
    meta = {"slug": "t", "bounds": BOUNDS,
            "instances": {"cellSize": 1000, "minX": -500, "minY": -300, "cellsX": 2, "cellsY": 1,
                          "treeCount": len(trees), "treeCells": ["0_0"]}}
    if stand is not None:
        os.makedirs(os.path.join(d, "stands"), exist_ok=True)
        p, hgt = stand
        sp = np.zeros_like(p, np.uint8); z = np.zeros_like(p)
        Image.fromarray(stands.encode(p, hgt, sp, z, 0.0), "RGB").save(os.path.join(d, "stands", "0_0.png"))
        meta["stands"] = {"res": 4, "size": 250, "zBase": 0.0, "zScale": 32, "hStep": 0.25, "cells": ["0_0"], "stems": 0}
    with open(os.path.join(d, "meta.json"), "w") as f:
        json.dump(meta, f)
    return d


def run(d):
    canopy.main([d])
    meta = json.load(open(os.path.join(d, "meta.json")))
    img, e = canopy.read(d, meta)
    return meta, img, e


def test_grid_orientation_and_references(tmp_path):
    # closed tall timber in the north-east (22 m spruce every 4 m), the same density of 6 m trees in the south-west,
    # and scattered 20 m trees (one per 25 m) in the south-east
    trees = np.concatenate([block(250, 50, 200, 4, 22.0), block(-450, -250, 200, 4, 6.0), block(250, -250, 200, 25, 20.0)])
    meta, img, e = run(make_pack(str(tmp_path / "p"), trees))
    assert e == {"res": 10.0, "minX": -500.0, "minY": -300.0, "w": 101, "h": 60, "file": "canopy.png"}
    assert img.shape == (60, 101) and Image.open(tmp_path / "p" / "canopy.png").mode == "L"
    # row 0 is the north edge (minY + h * res), column 0 the west edge: the timber is in the top right
    assert img[:30, 51:].max() == 1.0 and img[30:, 51:].max() < 0.2
    assert img[10:20, 80:90].min() == 1.0                  # y 250..150, x 300..400: inside the timber
    assert canopy.sample(img, e, 350, 150) == 1.0
    assert canopy.sample(img, e, -350, -150) == 0.0          # short trees make no canopy, however dense
    assert canopy.sample(img, e, 350, -150) < 0.2            # scattered tall trees read as open
    assert canopy.sample(img, e, -100, 0) == 0.0             # bare ground
    assert canopy.sample(img, e, 9000, 0) == 0.0             # off the grid
    # the edge fades over a few cells instead of a step
    edge = [canopy.sample(img, e, 350, y) for y in range(0, 80, 5)]
    assert edge == sorted(edge) and edge[0] < 0.1 and edge[-1] == 1.0 and sum(0.2 < v < 0.8 for v in edge) >= 2
    assert meta.get("build")   # a new build, so the game's get --from copies it again


def test_reference_is_absolute_not_per_pack(tmp_path):
    """a pack of only scattered trees does not stretch them to 1: the references are fixed amounts"""
    meta, img, e = run(make_pack(str(tmp_path / "p"), block(250, -250, 200, 25, 20.0)))
    assert img.max() < 0.2


def test_stems_count_by_their_height(tmp_path):
    """FEAT-074: the generated stems count in expectation; a stand under MIN_H counts for nothing"""
    p = np.zeros((250, 250), np.float32); hgt = np.zeros_like(p)
    # rows 0.. are the north of the 1 km cell (y 700 down); the bounds reach y 300, rows 100.. are inside
    p[110:160, 10:60] = 1.0; hgt[110:160, 10:60] = 22.0     # a closed tall stand, x -460..-260, y 260..60
    p[110:160, 150:200] = 1.0; hgt[110:160, 150:200] = 9.0  # a closed low one, x 100..300
    _meta, img, e = run(make_pack(str(tmp_path / "p"), np.zeros((0, 6), np.float32), (p, hgt)))
    assert canopy.sample(img, e, -360, 160) > 0.9
    assert canopy.sample(img, e, 200, 160) == 0.0


def test_volume_reads_crown_cover_times_height():
    """v is crown area x height over the cell area: one 20 m tree of 3 m radius in a 10 m cell is pi * 9 * 20 / 100"""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        t = np.array([[5, 5, 0, 20.0, 2.6, 0]], np.float32)   # spruce, 0.13 x 20 = 2.6 m
        make_pack(d, t)
        meta = json.load(open(os.path.join(d, "meta.json")))
        v = canopy.canopy_volume(d, meta)
        # x 5 is column (5 + 500) // 10 = 50, y 5 row (300 - 5) // 10 = 29 from the top
        assert abs(v[29, 50] - np.pi * 2.6 ** 2 * 20 / 100) < 1e-3 and v.sum() == v[29, 50]


def test_missing_grid_reads_none(tmp_path):
    d = tmp_path / "p"; d.mkdir()
    assert canopy.read(str(d), {"bounds": BOUNDS}) == (None, None)
