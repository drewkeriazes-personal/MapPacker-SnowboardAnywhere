"""FEAT-379: the traffic map (traffic.py) on a small pack: a slope falling south, a lift up its west side, a groomer down
beside it, a cat track across the top to an ungroomed run down the east side, trees between. The layer is on the mask's
grid in the agreed encoding, riders spread across a groomer with a peak in its middle, go along the cat track as one,
fan out on the off-piste run, follow a tree line downhill whichever way its file lists it, and come out the same every
build; a pack with no runs gets no layer."""
import json, os, sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import traffic  # noqa: E402
from packwriter import write_height_set, write_mask_set  # noqa: E402

B = {"minX": -400, "minY": -600, "maxX": 400, "maxY": 600}
GROOMER_X, OFF_X, TRACK_Y = -150.0, 250.0, 520.0


def ground(x, y):
    """falls 0.4 m per m to the south"""
    return 3000 + 0.4 * np.asarray(y, np.float64) + 0 * np.asarray(x, np.float64)


def line(pts):
    return [[float(x), float(y), float(ground(x, y))] for x, y in pts]


def runs():
    ys = np.arange(540, -560, -40.0)
    return [
        {"name": "Groomer", "difficulty": "intermediate", "groomed": True, "gladed": False, "area": False, "osmId": 1,
         "points": line([(GROOMER_X, y) for y in ys])},
        # across the slope, dropping 0.05 m per m (a road): its own drop is far less than the ground's
        {"name": "Cat Track", "difficulty": "easy", "groomed": True, "gladed": False, "area": False, "osmId": 2,
         "points": [[float(x), TRACK_Y, float(ground(0, TRACK_Y) - 0.05 * (x + 130))] for x in np.arange(-130, OFF_X + 1, 20.0)]},
        {"name": "Chute", "difficulty": "expert", "groomed": False, "gladed": False, "area": False, "osmId": 3,
         "points": line([(OFF_X, y) for y in np.arange(TRACK_Y - 5, -520, -40.0)])},
    ]


def lifts():
    return [{"name": "Lift", "type": "chair_lift", "capacity": 2400,
             "stations": line([(GROOMER_X - 40, -570), (GROOMER_X - 40, 560)])}]


def make_pack(d, rs=None, tree_lines=None):
    os.makedirs(d, exist_ok=True)
    rs = runs() if rs is None else rs
    xs = np.arange(B["minX"], B["maxX"]) + 0.5
    ys = np.arange(B["maxY"], B["minY"], -1) - 0.5
    X, Y = np.meshgrid(xs, ys)
    fine = write_height_set(d, "fine", ground(X, Y).astype(np.float32), 1.0, B["minX"], B["minY"])
    # mask at 2 m: groomed 14 m either side of a groomed line, canopy everywhere off the runs but a 40 m open chute
    xs2 = np.arange(B["minX"], B["maxX"], 2.0) + 1
    ys2 = np.arange(B["maxY"], B["minY"], -2.0) - 1
    X2, Y2 = np.meshgrid(xs2, ys2)
    groomed = (np.abs(X2 - GROOMER_X) <= 14) | ((np.abs(Y2 - TRACK_Y) <= 5) & (X2 > -140) & (X2 < OFF_X + 5))
    open_ = groomed | ((np.abs(X2 - OFF_X) <= 40) & (Y2 < TRACK_Y + 5))
    rgba = np.zeros(X2.shape + (4,), np.uint8)
    rgba[..., 2] = np.where(groomed, 255, 0)
    rgba[..., 3] = np.where(open_, 0, 255)
    mask = write_mask_set(d, rgba, 2.0, B["minX"], B["minY"])
    meta = {"slug": "t", "bounds": B, "terrain": {"fine": fine}, "mask": mask}
    if tree_lines is not None:
        with open(os.path.join(d, "treeLines.json"), "w") as f:
            json.dump({"version": 1, "step": 3.0, "lines": tree_lines}, f)
        meta["treeLines"] = {"file": "treeLines.json", "lines": len(tree_lines)}
    with open(os.path.join(d, "meta.json"), "w") as f:
        json.dump(meta, f)
    with open(os.path.join(d, "features.json"), "w") as f:
        json.dump({"runs": rs, "lifts": lifts()}, f)
    return d


def built(d):
    traffic.main([d])
    meta = json.load(open(os.path.join(d, "meta.json")))
    rgb, g = traffic.read_traffic(d, meta)
    vx, vy, den = traffic.decode(rgb)
    at = lambda x, y: (int((g.yT - y) / traffic.RES), int((x - g.x0) / traffic.RES))
    return meta, rgb, (vx, vy, den), at


def test_layer_on_the_mask_grid_in_the_agreed_encoding(tmp_path):
    d = make_pack(str(tmp_path / "p"))
    meta, rgb, (vx, vy, den), at = built(d)
    t = meta["traffic"]
    assert set(t) == {"res", "tileSize", "minX", "minY", "tilesX", "tilesY"}
    assert t["res"] == 4.0 and t["tileSize"] == 256
    assert (t["minX"], t["minY"]) == (meta["mask"]["minX"], meta["mask"]["minY"])
    # 256 px at 4 m covers what the mask's 512 px at 2 m do
    assert t["tilesX"] * t["tileSize"] * t["res"] == meta["mask"]["tilesX"] * 512 * meta["mask"]["res"]
    for tx in range(t["tilesX"]):
        for ty in range(t["tilesY"]):
            im = Image.open(os.path.join(d, "traffic", f"{tx}_{ty}.png"))
            assert im.mode == "RGB" and im.size == (256, 256)
    # nobody rides there: no direction either
    none = rgb[..., 2] == 0
    assert none.any() and np.all(rgb[none][:, :2] == 128)
    assert np.all(np.hypot(vx, vy) <= 1.0 + 2 / 255)
    # the pack lint knows the set
    import pack_lint
    assert "traffic" in pack_lint.TILE_SETS


def test_groomer_broad_peak_down_the_fall_line(tmp_path):
    d = make_pack(str(tmp_path / "p"))
    _, _, (vx, vy, den), at = built(d)
    y = 0.0
    mid = den[at(GROOMER_X, y)]
    edge = den[at(GROOMER_X + 12, y)]
    out = den[at(GROOMER_X + 60, y)]
    assert mid > 0.3
    assert mid > edge > out
    assert den[at(GROOMER_X + 4, y)] > 0.8 * mid   # broad, not a line
    assert vy[at(GROOMER_X, y)] < -0.7              # south, downhill
    assert abs(vx[at(GROOMER_X, y)]) < 0.3


def test_cat_track_along_its_axis_as_one(tmp_path):
    d = make_pack(str(tmp_path / "p"))
    _, _, (vx, vy, den), at = built(d)
    track = [(vx[at(x, TRACK_Y)], vy[at(x, TRACK_Y)], den[at(x, TRACK_Y)]) for x in (0.0, 60.0, 120.0)]
    for x_, y_, d_ in track:
        assert d_ > 0.2
        assert x_ > 0.85               # east, along the track (its downhill sense), with high coherence
    groomer = np.hypot(vx[at(GROOMER_X, 0)], vy[at(GROOMER_X, 0)])
    assert min(np.hypot(a, b) for a, b, _ in track) > groomer   # turning riders spread their directions more


def test_off_piste_fans_out_from_its_entry(tmp_path):
    d = make_pack(str(tmp_path / "p"))
    _, _, (vx, vy, den), at = built(d)

    def width(y):
        r, c = at(OFF_X, y)
        row = den[r, c - 25:c + 26]
        return int((row > 0.5 * row.max()).sum()) if row.max() > 0 else 0

    assert den[at(OFF_X, 200)] > 0.1
    assert width(100) > width(TRACK_Y - 15)
    assert vy[at(OFF_X, 100)] < -0.5


def test_tree_line_downhill_whichever_way_listed(tmp_path):
    # listed bottom to top, in the trees west of the chute
    pts = []
    for y in np.arange(-300, 300, 3.0):
        pts += [120.0, float(y), 1.2, 1.0]
    d = make_pack(str(tmp_path / "p"), tree_lines=[{"p": pts}])
    _, _, (vx, vy, den), at = built(d)
    assert den[at(120, 0)] > 0.05
    assert vy[at(120, 0)] < -0.7


def test_same_pack_same_map(tmp_path):
    a = make_pack(str(tmp_path / "a")); b = make_pack(str(tmp_path / "b"))
    _, ra, _, _ = built(a); _, rb, _, _ = built(b)
    assert np.array_equal(ra, rb)


def test_no_runs_no_layer(tmp_path):
    d = make_pack(str(tmp_path / "p"), rs=[])
    traffic.main([d])
    meta = json.load(open(os.path.join(d, "meta.json")))
    assert "traffic" not in meta and not os.path.exists(os.path.join(d, "traffic"))


def test_runs_and_lift_starting_past_the_bounds(tmp_path, monkeypatch):
    # as the synthetic pack: the lift's top and the runs' tops lie north of the bounds; riders start where they come in
    far = runs()
    far[0]["points"] = line([(GROOMER_X, y) for y in np.arange(700, -560, -40.0)])
    monkeypatch.setattr(sys.modules[__name__], "lifts", lambda: [{"name": "Lift", "type": "chair_lift", "capacity": 4,
                        "stations": line([(GROOMER_X - 40, -570), (GROOMER_X - 40, 690)])}])
    d = make_pack(str(tmp_path / "p"), rs=far)
    meta, _, (vx, vy, den), at = built(d)
    assert "traffic" in meta
    assert den[at(GROOMER_X, 0)] > 0.3 and vy[at(GROOMER_X, 0)] < -0.7
