"""FEAT-345: a cloud build carries the published menu (ghost takes, still, shots) over from the release zip, keeps
the takes that still sit on the new heights, and keeps a still only when the pack is the published one."""
import io
import json
import os
import shutil
import sys
import zipfile

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools", "ci"))
import build_pack_ci as ci  # noqa: E402
import gen_content as gc  # noqa: E402
import publish_pack  # noqa: E402
import release_zip as rz  # noqa: E402
from test_pack_report import ground, make_pack  # noqa: E402

QUIET = dict(log=lambda s: None)


def take(dz=0.0, n=60):
    """a ghost take down the demo pack's Main run (x = 100, heading south), `dz` m above the ground"""
    ys = np.linspace(280, 120, n)
    return {"version": 1, "pack": "demo", "shot": "s", "build": "old", "samples": [
        {"t": i * 0.05, "x": 100.0, "y": float(y), "z": float(ground(100.0, y)) + dz, "f": 1} for i, y in enumerate(ys)]}


def rendered(pack, shots, takes=None, build="old-build"):
    """`pack`/attract/ as auto_attract.mjs leaves it: the shots, a still of the first and its takes"""
    d = pack / "attract"
    d.mkdir(exist_ok=True)
    first = shots[0]["id"]
    takes = takes if takes is not None else {f"{first}-start-run-v1-1.json": take(), f"{first}-start-run-v1-2.json": take()}
    (d / "shots.json").write_text(json.dumps(shots, indent=2) + "\n", encoding="utf-8")
    (d / f"{first}.jpg").write_bytes(b"\xff\xd8 a still")
    for name, t in takes.items():
        (d / name).write_text(json.dumps(t), encoding="utf-8")
    idx = {"shots": True, "generated": True, "stills": [first], "ghosts": list(takes),
           "looks": {first: {"code": "c0de", "pack": build}}, "shotGhosts": {first: list(takes)}}
    (d / "index.json").write_text(json.dumps(idx, indent=2), encoding="utf-8")
    return idx


def zip_of(pack):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        for root, _, files in os.walk(pack):
            for f in files:
                full = os.path.join(root, f)
                z.write(full, os.path.relpath(full, pack).replace(os.sep, "/"))
    return buf.getvalue()


class Release:
    """a fake release server: serves `data` by ranges, counts the bytes read"""

    def __init__(self, data):
        self.data, self.read = data, 0

    def __call__(self, req, timeout=None):
        a, b = (int(v) for v in req.headers["Range"].removeprefix("bytes=").split("-"))
        self.read += b - a + 1

        class Resp(io.BytesIO):
            status = 206
        return Resp(self.data[a:b + 1])


def index_of(pack):
    return json.load(open(pack / "attract" / "index.json", encoding="utf-8"))


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """the demo pack as build_pack.py leaves it, and as published: its menu generated and rendered (built once)"""
    root = tmp_path_factory.mktemp("built")
    fresh = make_pack(root / "fresh")
    pub = root / "pub" / "demo"
    shutil.copytree(fresh, pub)
    _, shots = gc.generate(str(pub), **QUIET)
    rendered(pub, shots, build=json.load(open(pub / "meta.json"))["build"])
    return fresh, pub, shots


@pytest.fixture
def published(built, tmp_path, monkeypatch):
    """the published pack zipped as a release, and a fresh build of it with no attract/ (the runner's empty
    packs/<slug>/), its content stage not run yet"""
    pub, fresh = tmp_path / "pub", tmp_path / "packs" / "demo"
    shutil.copytree(built[1], pub)
    shutil.copytree(built[0], fresh)
    shots = built[2]
    srv = Release(zip_of(pub))
    monkeypatch.setattr(rz.urllib.request, "urlopen", srv)
    return {"pub": pub, "fresh": fresh, "shots": shots, "srv": srv, "url": "https://x/demo.zip", "size": len(srv.data)}


def test_carry_on_matching_cameras_keeps_the_riders_and_the_still(published):
    p = published
    got = rz.carry_attract(p["url"], p["size"], str(p["fresh"]), **QUIET)
    assert got["carried"] and len(got["ghosts"]) == 2 and got["stills"] == [p["shots"][0]["id"]]
    assert p["srv"].read < p["size"], "ranged reads, not the whole zip"
    assert sorted(os.listdir(p["fresh"] / "attract")) == sorted(os.listdir(p["pub"] / "attract"))
    gc.generate(str(p["fresh"]), **QUIET)                          # the content stage: the same cameras
    assert index_of(p["fresh"]) == index_of(p["pub"])
    for f in os.listdir(p["pub"] / "attract"):
        assert (p["fresh"] / "attract" / f).read_bytes() == (p["pub"] / "attract" / f).read_bytes()


def test_carry_on_changed_cameras_drops_them(published, monkeypatch):
    p = published
    rz.carry_attract(p["url"], p["size"], str(p["fresh"]), **QUIET)
    moved = [dict(s, x=s["x"] + 50) for s in p["shots"]]
    monkeypatch.setattr(gc, "choose_shots", lambda *a, **k: moved)
    gc.generate(str(p["fresh"]), **QUIET)
    idx = index_of(p["fresh"])
    assert idx["stills"] == [] and idx["ghosts"] == [] and sorted(os.listdir(p["fresh"] / "attract")) == \
        ["index.json", "shots.json"]


def test_a_take_off_the_new_heights_is_dropped(published):
    p = published
    first = p["shots"][0]["id"]
    rendered(p["pub"], p["shots"], takes={"a.json": take(0.1), "b.json": take(2.0), "c.json": take(-0.8)})
    p["srv"].data = zip_of(p["pub"])
    rz.carry_attract(p["url"], len(p["srv"].data), str(p["fresh"]), **QUIET)
    gc.generate(str(p["fresh"]), **QUIET)
    idx = index_of(p["fresh"])
    assert idx["ghosts"] == ["a.json"] and idx["shotGhosts"] == {first: ["a.json"]}
    assert not (p["fresh"] / "attract" / "b.json").exists() and not (p["fresh"] / "attract" / "c.json").exists()


def test_the_height_check_uses_the_95th_percentile_not_the_worst_sample(tmp_path):
    pack = make_pack(tmp_path / "packs")
    h = gc.FineHeights(str(pack), json.load(open(pack / "meta.json"))["terrain"]["fine"])
    t = take()
    assert gc.take_off_ground(t, h) < 0.2                      # the bilinear ground, as the game samples it
    t["samples"][10]["z"] += 3.0                                # one landing frame off: kept
    assert gc.take_off_ground(t, h) < gc.TAKE_OFF_M
    for s in t["samples"][:30]:                                 # half the run moved: dropped
        s["z"] += 1.0
    assert gc.take_off_ground(t, h) > gc.TAKE_OFF_M
    air = {"samples": [dict(s, f=0) for s in t["samples"]]}     # nothing on the ground: nothing to judge by
    assert gc.take_off_ground(air, h) is None


def test_listed_files_that_are_missing_leave_the_index(tmp_path):
    pack = make_pack(tmp_path / "packs")
    idx = rendered(pack, [{"id": "s"}], takes={"a.json": take(), "b.json": take()})
    os.remove(pack / "attract" / "b.json")
    os.remove(pack / "attract" / "s.jpg")
    assert gc.check_kept(str(pack), idx, **QUIET)
    got = index_of(pack)
    assert got["ghosts"] == ["a.json"] and got["stills"] == [] and got["looks"] == {}


@pytest.mark.parametrize("why, make", [
    ("HTTP error", lambda p: setattr(p["srv"], "data", b"not a zip" * 40)),
    ("a listed file missing", None),
])
def test_a_failed_read_carries_nothing(published, why, make):
    p = published
    if make:
        make(p)
    else:
        idx = index_of(p["pub"])
        idx["ghosts"].append("gone.json")
        (p["pub"] / "attract" / "index.json").write_text(json.dumps(idx))
        p["srv"].data = zip_of(p["pub"])
    with pytest.raises(OSError):
        rz.carry_attract(p["url"], len(p["srv"].data), str(p["fresh"]), **QUIET)
    assert not (p["fresh"] / "attract").exists(), "nothing half-written"
    # the CI step logs it and builds on: today's output, the shots and nothing else
    line = ci.carry_menu("demo", str(p["fresh"]), {"url": p["url"], "bytes": len(p["srv"].data)})
    assert line.startswith("menu not carried")
    gc.generate(str(p["fresh"]), **QUIET)
    assert index_of(p["fresh"])["ghosts"] == [] and index_of(p["fresh"])["stills"] == []


def test_nothing_to_carry(published, tmp_path):
    p = published
    assert ci.carry_menu("demo", str(p["fresh"]), None) == "no published menu"
    assert ci.carry_menu("demo", str(p["fresh"]), {"bytes": 5}) == "no published menu"
    hand = index_of(p["pub"])
    del hand["generated"]                                     # a hand-made menu: resorts/<slug>/attract/ makes it
    (p["pub"] / "attract" / "index.json").write_text(json.dumps(hand))
    p["srv"].data = zip_of(p["pub"])
    got = rz.carry_attract(p["url"], len(p["srv"].data), str(p["fresh"]), **QUIET)
    assert not got["carried"] and "hand-made" in got["why"] and not (p["fresh"] / "attract").exists()
    (p["fresh"] / "attract").mkdir()                            # a pack folder that has one: left alone
    (p["fresh"] / "attract" / "index.json").write_text("{}")
    assert not rz.carry_attract(p["url"], len(p["srv"].data), str(p["fresh"]), **QUIET)["carried"]


def test_a_bad_name_in_the_index_is_refused():
    with pytest.raises(ValueError):
        rz.attract_files({"stills": [], "ghosts": ["../../meta.json"]})


def test_the_still_stays_only_when_the_pack_is_the_published_one(published):
    p = published
    rz.carry_attract(p["url"], p["size"], str(p["fresh"]), **QUIET)
    gc.generate(str(p["fresh"]), **QUIET)
    meta = json.load(open(p["fresh"] / "meta.json"))
    meta["build"] = "new-build"                                 # a cloud build always has a new build stamp
    (p["fresh"] / "meta.json").write_text(json.dumps(meta))
    first = p["shots"][0]["id"]
    assert gc.stale_stills(str(p["fresh"])) == [first]
    # the same pack as published (content key equal): nothing will publish, the published still stays right
    key = publish_pack.content_key(str(p["fresh"]))
    assert key == publish_pack.content_key(str(p["pub"]))       # build stamps aside, the very same pack
    assert ci.settle_stills(str(p["fresh"]), {"content": key}) == "the pack is unchanged: still kept"
    assert index_of(p["fresh"])["stills"] == [first] and (p["fresh"] / "attract" / f"{first}.jpg").exists()
    # changed (or published before content keys): the still goes, the riders stay, no entry names a missing still
    line = ci.settle_stills(str(p["fresh"]), {"content": "0000000000000000"})
    assert "still dropped" in line
    idx = index_of(p["fresh"])
    assert idx["stills"] == [] and idx["looks"] == {} and len(idx["ghosts"]) == 2
    assert not (p["fresh"] / "attract" / f"{first}.jpg").exists()
    assert ci.settle_stills(str(p["fresh"]), {}) == ""          # nothing left to settle


def test_a_still_of_this_very_build_is_never_stale(tmp_path):
    pack = make_pack(tmp_path / "packs")
    rendered(pack, [{"id": "s"}], build=json.load(open(pack / "meta.json"))["build"])
    assert gc.stale_stills(str(pack)) == []
    assert ci.settle_stills(str(pack), None) == ""


def test_the_build_step_carries_before_and_settles_after(tmp_path, monkeypatch):
    resorts = tmp_path / "resorts"
    os.makedirs(resorts / "demo")
    (resorts / "demo" / "demo.json").write_text(json.dumps({"name": "Demo"}))
    monkeypatch.setattr(ci, "from_env", lambda: ci.check_inputs("", "", "demo", "", str(resorts)))
    monkeypatch.setattr(ci.paths, "PACKS", str(tmp_path / "packs"))
    monkeypatch.setattr(ci, "published_pack", lambda slug: {"url": "https://x/demo.zip", "bytes": 10})
    summ = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summ))
    order = []

    def carry(url, size, pack_dir, log):
        order.append("carry")
        raise OSError("HTTP 404")
    assert ci.main(["build"], runner=lambda cmd: (order.append("build"), (0, "ok"))[1], carry=carry) == 0
    assert order == ["carry", "build"]
    assert summ.read_text(encoding="utf-8").startswith("| build | done; menu not carried (HTTP 404) |")
