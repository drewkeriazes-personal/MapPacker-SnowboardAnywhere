"""FEAT-334: glade tree lines from the terrain (tree_lines.py) on a small pack: a slope falling south into a gully, a
lattice of trunks with jitter, one expert run down it. The lines run downhill, keep every trunk out of their corridors,
merge as they go down, come out the same every build, and a pack with no line runs gets none. FEAT-378: they cut back
and forth on the steep and run nearly straight on the gentle, and never turn tighter than the trench draws."""
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


def make_pack(d, runs, ground=ground):
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


def run_down(diff="expert", ground=ground):
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
    # riders join the lines below them: the 60-odd riders seeded on this slope come down a handful of lines low down
    # (FEAT-378: riders turning back and forth, and the odd fork round a trunk, make the count up top no guide), and
    # the busiest low one carries STR_RIDERS riders or more, and others two or more
    low = across(-300)
    assert 2 <= len(low) <= 8
    assert max(low) == 1.0 and sum(v >= 0.7 for v in low) >= 2


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


def gentle(x, y):
    """falls 0.15 m per m to the south (8.5 degrees), no gully"""
    return 2000 + 0.15 * y + 0 * x


def test_lines_turn_on_the_steep_and_run_straight_on_the_gentle(tmp_path):
    d, _ = make_pack(str(tmp_path / "steep"), [run_down()])
    tree_lines.main([d])
    meta = json.load(open(os.path.join(d, "meta.json")))
    lines = json.load(open(os.path.join(d, "treeLines.json")))["lines"]
    st = tree_lines.straightness(lines, tree_lines.Heights(d, meta))
    # 27 degrees: linked turns finishing well across the hill, most of each line off the fall line
    assert st["sinuosity30"]["median"] > 1.05 and st["sinuosity90"]["median"] > 1.1
    assert st["drift60"]["median"] > 5
    assert st["fallLine"]["25-35"] < 0.5
    g, _ = make_pack(str(tmp_path / "gentle"), [run_down(ground=gentle)], ground=gentle)
    tree_lines.main([g])
    meta = json.load(open(os.path.join(g, "meta.json")))
    lines = json.load(open(os.path.join(g, "treeLines.json")))["lines"]
    sg = tree_lines.straightness(lines, tree_lines.Heights(g, meta))
    # 8.5 degrees: nearly straight, gentle wiggles
    assert sg["sinuosity30"]["median"] < 1.03 and sg["sinuosity30"]["median"] < st["sinuosity30"]["median"]
    assert sg["fallLine"]["0-15"] > st["fallLine"]["25-35"]


def test_no_turn_tighter_than_the_trench_draws(tmp_path):
    d, _ = make_pack(str(tmp_path / "p"), [run_down()])
    tree_lines.main([d])
    for p in lines_of(d):
        v = np.diff(p[:, :2], axis=0)
        a = np.abs(np.arctan2(v[:-1, 0] * v[1:, 1] - v[:-1, 1] * v[1:, 0], (v[:-1] * v[1:]).sum(1)))
        # the turn between two STEP m segments of a circle of radius R is STEP / R
        assert np.all(a <= tree_lines.STEP / tree_lines.R_MIN + 0.02)


def test_straightness_report(tmp_path):
    d, _ = make_pack(str(tmp_path / "p"), [run_down()])
    meta = json.load(open(os.path.join(d, "meta.json")))
    y = np.arange(500, 0, -3.0)
    straight = np.stack([np.full(len(y), 100.0), y, np.ones(len(y)), np.ones(len(y))], 1)
    zig = straight.copy(); zig[:, 0] += 24 * np.abs(((y / 24) % 2) - 1)   # 45 degrees off the fall line, back and forth
    st = tree_lines.straightness([{"p": straight.ravel().tolist()}], tree_lines.Heights(d, meta))
    assert st["lines"] == 1 and st["sinuosity30"]["median"] < 1.001 and st["drift60"]["median"] < 0.01
    assert st["fallLine"]["25-35"] > 0.99
    sz = tree_lines.straightness([{"p": zig.ravel().tolist()}], tree_lines.Heights(d, meta))
    assert 1.2 < sz["sinuosity30"]["median"] < 1.5 and sz["fallLine"]["25-35"] < 0.01
    # near a run: only the lines that come within NEAR_M of it
    far = straight.copy(); far[:, 0] += 1000
    assert tree_lines.straightness([{"p": far.ravel().tolist()}, {"p": straight.ravel().tolist()}], tree_lines.Heights(d, meta),
                                   near=[[[100.0, 0.0], [100.0, 500.0]]])["lines"] == 1


def middling(x, y):
    """falls 0.25 m per m to the south (14 degrees), no gully"""
    return 2000 + 0.25 * y + 0 * x


def test_no_long_straight_lane_in_the_trees(tmp_path):
    """FEAT-378 v2: on a 14 degree glade the lines break a straight lane with S-turns round the trunks"""
    d, _ = make_pack(str(tmp_path / "p"), [run_down(ground=middling)], ground=middling)
    tree_lines.main([d])
    meta = json.load(open(os.path.join(d, "meta.json")))
    st = meta["treeLines"]["checks"]["straightness"]
    assert st["sTurnsPerKm"] > 0.5
    from scipy.spatial import cKDTree
    t = np.fromfile(os.path.join(d, "trees", "0_0.bin"), "<f4").reshape(-1, 6)
    s = tree_lines.straightness(json.load(open(os.path.join(d, "treeLines.json")))["lines"], tree_lines.Heights(d, meta),
                                trunks=cKDTree(t[:, :2]))
    cap = tree_lines.STRAIGHT_MAX[0] * (1 + tree_lines.STRAIGHT_JITTER)
    assert s["straightInTrees"]["0-15"]["p90"] <= cap + 10


def test_lines_keep_out_of_tree_wells(tmp_path):
    """FEAT-378 v2: a line's centreline keeps a conifer's crown radius (2.3 m here) from its trunk (Sun Peaks glade safety:
    out of the tree well and the low boughs)"""
    d, trunks = make_pack(str(tmp_path / "p"), [run_down()])
    tree_lines.main([d])
    from scipy.spatial import cKDTree
    kd = cKDTree(trunks[:, :2].astype(np.float64))
    dd = np.concatenate([kd.query(p[p[:, 3] > 0.15, :2])[0] for p in lines_of(d)])
    # all clear of the trunk by BLOCK (a line squeezing past one, where it fades round a break), nearly all of the well
    assert dd.min() > tree_lines.BLOCK - 0.3 and np.mean(dd > 2.3 - 0.3) > 0.98
