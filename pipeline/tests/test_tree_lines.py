"""FEAT-334: glade tree lines from the terrain (tree_lines.py) on a small pack: a slope falling south into a gully, a
lattice of trunks with jitter, one expert run down it. The lines run downhill, keep every trunk out of their corridors,
merge as they go down, come out the same every build, and a pack with no line runs gets none."""
import json, os, sys
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import tree_lines  # noqa: E402
from packwriter import write_height_set  # noqa: E402

GULLY = -20.0
B = {"minX": -400, "minY": -600, "maxX": 400, "maxY": 600}


def ground(x, y):
    """falls 0.5 m per m to the south, plus a gully along x = GULLY (80 m east of the run) that deepens downhill"""
    return 2000 + 0.5 * y - 15 * np.exp(-((x - GULLY) / 30) ** 2) * (600 - y) / 1200


def make_pack(d, runs):
    os.makedirs(os.path.join(d, "trees"), exist_ok=True)
    xs = np.arange(B["minX"], B["maxX"]) + 0.5
    ys = np.arange(B["maxY"], B["minY"], -1) - 0.5
    X, Y = np.meshgrid(xs, ys)
    fine = write_height_set(d, "fine", ground(X, Y).astype(np.float32), 1.0, B["minX"], B["minY"])
    rng = np.random.default_rng(3)
    tx, ty = np.meshgrid(np.arange(-390, 390, 9.0), np.arange(-590, 590, 9.0))
    tx = tx.ravel() + rng.uniform(-3, 3, tx.size); ty = ty.ravel() + rng.uniform(-3, 3, ty.size)
    keep = np.abs(tx + 100) > 14   # the run's own corridor is clear
    tx, ty = tx[keep], ty[keep]
    n = len(tx)
    t = np.stack([tx, ty, ground(tx, ty), np.full(n, 18.0), np.full(n, 2.3), np.zeros(n)], 1).astype("<f4")
    t.tofile(os.path.join(d, "trees", "0_0.bin"))
    meta = {"slug": "t", "bounds": B, "terrain": {"fine": fine},
            "instances": {"cellSize": 2000, "minX": B["minX"], "minY": B["minY"], "cellsX": 1, "cellsY": 1,
                          "treeCount": n, "treeCells": ["0_0"]}}
    with open(os.path.join(d, "meta.json"), "w") as f:
        json.dump(meta, f)
    with open(os.path.join(d, "features.json"), "w") as f:
        json.dump({"runs": runs}, f)
    return d, t


def run_down(diff="expert"):
    y = np.arange(560, -560, -40.0)
    return {"name": "Glade", "difficulty": diff, "gladed": False, "area": False, "osmId": 7,
            "points": [[-100.0, float(v), float(ground(-100.0, v))] for v in y]}


def lines_of(d):
    return [np.asarray(ln["p"]).reshape(-1, 4) for ln in json.load(open(os.path.join(d, "treeLines.json")))["lines"]]


def crossings(lines, y, x0, x1):
    n = 0
    for p in lines:
        for i in range(len(p) - 1):
            (ax, ay, _, sa), (bx, by, _, sb) = p[i], p[i + 1]
            if (ay - y) * (by - y) < 0 and min(sa, sb) > 0.3 and x0 <= ax + (bx - ax) * (y - ay) / (by - ay) <= x1:
                n += 1
    return n


def test_lines_follow_the_ground_and_clear_the_trunks(tmp_path):
    d, trunks = make_pack(str(tmp_path / "p"), [run_down()])
    tree_lines.main([d])
    meta = json.load(open(os.path.join(d, "meta.json")))
    e = meta["treeLines"]
    assert e["file"] == "treeLines.json" and e["lines"] > 5 and e["km"] > 1
    assert e["checks"]["trunksInCorridor"] == 0
    lines = lines_of(d)
    assert len(lines) == e["lines"]
    for p in lines:
        assert np.all((p[:, 2] >= tree_lines.SQUEEZE_HW - 1e-6) & (p[:, 2] <= tree_lines.HW_NEAR * 1.31))
        assert np.all((p[:, 3] >= 0) & (p[:, 3] <= 1))
        # downhill: every line ends lower than it starts, and never climbs much along the way
        z = ground(p[:, 0], p[:, 1])
        assert z[-1] < z[0] - 5
        assert np.max(np.diff(z)) < 1.0
        # no line in the run itself above its foot (the last FOOT_M m, from the run point before it, where the lines get out)
        above = p[:, 1] > -520 + tree_lines.FOOT_M + 40 + 10
        if above.any():
            assert np.min(np.abs(p[above, 0] + 100)) > tree_lines.RUN_KEEP["expert"] - 0.5
    # no trunk inside a strong corridor (checked here from the file, not the planner's own count)
    for p in lines:
        for i in range(len(p) - 1):
            if p[i, 3] < 0.15:
                continue
            a, b = p[i, :2], p[i + 1, :2]
            near = trunks[(np.abs(trunks[:, 0] - a[0]) < 6) & (np.abs(trunks[:, 1] - a[1]) < 6)]
            for t in near:
                assert tree_lines.seg_dist(t[:2].astype(np.float64), a, b) >= p[i, 2] - 1e-6


def test_lines_merge_down_the_slope(tmp_path):
    d, _ = make_pack(str(tmp_path / "p"), [run_down()])
    tree_lines.main([d])
    lines = lines_of(d)

    def across(y):
        """the strengths of the lines crossing the slope at y, both sides of the run, clear of its edge"""
        out = []
        for p in lines:
            for (ax, ay, _, sa), (bx, by, _, sb) in zip(p[:-1], p[1:]):
                if (ay - y) * (by - y) < 0 and min(sa, sb) > 0.3 and abs(ax + (bx - ax) * (y - ay) / (by - ay) + 100) > 12:
                    out.append(min(sa, sb))
        return out
    # riders join the lines below them: fewer separate lines low down than up top, and the low ones carry more riders
    up, low = across(200), across(-300)
    assert len(up) >= 5 and len(low) < len(up)
    assert np.mean(low) > np.mean(up)


def test_same_lines_every_build(tmp_path):
    d, _ = make_pack(str(tmp_path / "p"), [run_down()])
    tree_lines.main([d])
    a = open(os.path.join(d, "treeLines.json")).read()
    tree_lines.main([d])
    assert open(os.path.join(d, "treeLines.json")).read() == a


def test_no_line_runs_no_lines(tmp_path):
    d, _ = make_pack(str(tmp_path / "p"), [run_down("intermediate")])
    open(os.path.join(d, "treeLines.json"), "w").write("{}")   # a stale file from an earlier build goes
    tree_lines.main([d])
    assert "treeLines" not in json.load(open(os.path.join(d, "meta.json")))
    assert not os.path.exists(os.path.join(d, "treeLines.json"))
