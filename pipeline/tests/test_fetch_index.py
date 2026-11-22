"""FEAT-346: a raw file is kept while the manifest still wants the same bytes, and fetched again once it doesn't."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import fetch_index as F  # noqa: E402
from test_build_resort import Fake, go, resort  # noqa: E402,F401  (the build_resort fixture)
import build_resort as B  # noqa: E402

NAIP = {"url": "https://pc/api/data/v1/item/crop/0,0,9,9/9x9.tif?item=x", "path": "naip1m/x_0_0.tif",
        "meta": {"bbox": [0, 0, 9, 9], "size": [9, 9], "res": 1, "item": "x"}}
TILE = {"url": "https://tiles/12/1/2.webp", "path": "mapterhorn/12/1_2.webp"}


def put(raw, item, text="x"):
    path = os.path.join(raw, *item["path"].split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").write(text)
    return path


def test_a_meta_items_key_follows_its_meta_not_its_url():
    renamed = dict(NAIP, url=NAIP["url"].replace("/crop/", "/bbox/"))
    assert F.item_key(renamed) == F.item_key(NAIP)                      # the host renamed its route: same bytes
    assert F.item_key(dict(NAIP, meta=dict(NAIP["meta"], bbox=[0, 0, 9, 10]))) != F.item_key(NAIP)
    assert F.item_key(dict(TILE, url="https://tiles/12/1/3.webp")) != F.item_key(TILE)   # no meta: the url
    assert F.item_key(dict(TILE, path="mapterhorn/12/1_3.webp")) != F.item_key(TILE)


def test_prune_deletes_only_what_changed(tmp_path):
    raw = str(tmp_path)
    naip, tile = put(raw, NAIP), put(raw, TILE)
    F.record(raw, [NAIP, TILE])
    moved = dict(TILE, url="https://tiles/13/1/2.webp")
    assert F.prune(raw, [dict(NAIP, url="https://pc/new"), moved]) == [TILE["path"]]
    assert os.path.isfile(naip) and not os.path.exists(tile)


def test_a_folder_from_before_the_index_is_trusted(tmp_path):
    raw = str(tmp_path)
    naip = put(raw, NAIP)
    assert F.prune(raw, [dict(NAIP, meta={"other": 1})]) == []
    assert os.path.isfile(naip)


def test_a_path_out_of_the_raw_folder_is_refused(tmp_path):
    raw = str(tmp_path / "raw")
    os.makedirs(raw)
    json.dump({"../x": "old"}, open(os.path.join(raw, F.INDEX), "w"))
    with pytest.raises(ValueError, match="outside the raw folder"):
        F.prune(raw, [{"url": "u", "path": "../x"}])


def test_the_fetch_stage_prunes_first_and_records_after(resort, capsys):
    go(resort, Fake(resort))
    index = F.load(resort.raw)
    assert list(index) == ["dem1m/a.tif"]                      # the Fake manifest's one item
    stale = put(resort.raw, {"path": "dem1m/a.tif"})
    json.dump(dict(json.load(open(resort.cfg_path)), utm_bbox=[0, 0, 2000, 1000]), open(resort.cfg_path, "w"))
    r = B.Resort("demo", resort.raw, resort.out, resort.resorts, resort.manifests)
    go(r, Fake(r))                                               # the box moved: the manifest item's url changed
    assert not os.path.exists(stale)
    assert "1 file(s) fetched for an older manifest item, fetched again: dem1m/a.tif" in capsys.readouterr().out
    assert F.load(resort.raw)["dem1m/a.tif"] != index["dem1m/a.tif"]


def test_a_failed_fetch_records_nothing(resort):
    with pytest.raises(B.Failed):
        go(resort, Fake(resort, fetch_code=2))
    assert F.load(resort.raw) == {}


# ------------------------------------------------------------------------------------------------ FEAT-348: age

from datetime import datetime, timedelta, timezone  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools", "ci"))
import raw_cache  # noqa: E402

NOW = datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc)
OSM = {"url": "https://overpass/api/interpreter?data=ski", "path": "osm/ski.json"}


def days_ago(n):
    return NOW - timedelta(days=n)


def test_osm_has_a_maximum_age_and_the_other_layers_none():
    assert F.max_age("osm/ski.json") == 14
    assert [F.max_age(i["path"]) for i in (NAIP, TILE)] == [None, None]


def test_osm_fetched_15_days_ago_goes_again_and_yesterdays_stays(tmp_path):
    raw = str(tmp_path)
    osm, naip = put(raw, OSM), put(raw, NAIP)
    F.record(raw, [OSM, NAIP], [OSM["path"], NAIP["path"]], days_ago(15))
    assert F.over_age(raw, [OSM, NAIP], NOW) == [OSM["path"]]        # NAIP, as old, has no maximum age
    assert F.prune(raw, [OSM, NAIP], NOW) == [OSM["path"]]
    assert not os.path.exists(osm) and os.path.isfile(naip)
    put(raw, OSM)
    F.record(raw, [OSM, NAIP], [OSM["path"]], days_ago(1))
    assert F.load(raw)[NAIP["path"]]["fetched"] == F.stamp(days_ago(15))   # not fetched again: its time stays
    assert F.over_age(raw, [OSM, NAIP], NOW) == [] and F.prune(raw, [OSM, NAIP], NOW) == []
    assert os.path.isfile(os.path.join(raw, "osm", "ski.json"))


def test_an_index_in_the_old_form_is_read_and_rewritten_with_nothing_deleted(tmp_path):
    raw = str(tmp_path)
    osm, naip = put(raw, OSM), put(raw, NAIP)
    json.dump({OSM["path"]: F.item_key(OSM), NAIP["path"]: F.item_key(NAIP)}, open(os.path.join(raw, F.INDEX), "w"))
    assert F.load(raw)[OSM["path"]] == {"key": F.item_key(OSM), "fetched": None}
    assert F.over_age(raw, [OSM, NAIP], NOW) == [] and F.prune(raw, [OSM, NAIP], NOW) == []
    assert os.path.isfile(osm) and os.path.isfile(naip)
    F.record(raw, [OSM, NAIP], now=NOW)
    assert json.load(open(os.path.join(raw, F.INDEX))) == {
        OSM["path"]: {"key": F.item_key(OSM), "fetched": "2026-11-22T12:00:00Z"},
        NAIP["path"]: {"key": F.item_key(NAIP), "fetched": "2026-11-22T12:00:00Z"}}


def test_recording_a_folder_that_fetched_nothing_keeps_the_bytes_and_the_cache_key(tmp_path):
    """a rebuild from a restored cache records again: the index, and so the raw cache's key, must not change, or
    every build would upload the whole folder"""
    raw = str(tmp_path)
    put(raw, OSM), put(raw, NAIP), put(raw, TILE)
    F.record(raw, [TILE, OSM, NAIP], [OSM["path"], NAIP["path"], TILE["path"]], days_ago(3))
    before, key = open(os.path.join(raw, F.INDEX), "rb").read(), raw_cache.data_key(raw, raw_cache.saved_files(raw))
    F.record(raw, [NAIP, TILE, OSM], now=NOW)                                     # another order, a later clock
    assert open(os.path.join(raw, F.INDEX), "rb").read() == before
    assert raw_cache.data_key(raw, raw_cache.saved_files(raw)) == key
    F.record(raw, [NAIP, TILE, OSM], [OSM["path"]], NOW)                          # OSM fetched again
    assert raw_cache.data_key(raw, raw_cache.saved_files(raw)) != key             # the next save uploads it


def osm_build(r, clock):
    """the Fake manifest with an OSM item, so the fetch index has one"""
    fake = Fake(r)
    real = fake.__call__

    def run(cmd, cwd=None, env=None):
        code = real(cmd, cwd, env)
        if os.path.basename(cmd[1]) == "gen_manifest.py":
            m = json.load(open(r.man_path))
            m["items"].append({"url": "u-osm", "path": "osm/ski.json"})
            json.dump(m, open(r.man_path, "w"))
        if os.path.basename(cmd[cmd.index("-File") + 1] if "-File" in cmd else "") == "fetch.ps1" and not code:
            for item in json.load(open(r.man_path))["items"]:         # what a real fetch leaves: every item
                if not os.path.exists(os.path.join(r.raw, item["path"])):
                    put(r.raw, item, "fetched")
        return code
    run.calls = fake.calls
    lines = []
    B.build(r, B.Context(runner=run, email="me@example.com", clock=lambda: clock), out=lines.append)
    return run.calls, lines


def again(r):
    return B.Resort("demo", r.raw, r.out, r.resorts, r.manifests)


def test_old_osm_runs_the_fetch_stage_and_the_build_even_with_an_unchanged_manifest(resort, capsys):
    osm_build(resort, days_ago(15))
    assert F.load(resort.raw)["osm/ski.json"]["fetched"] == F.stamp(days_ago(15))
    calls, lines = osm_build(again(resort), days_ago(1))              # 14 days later: young enough
    assert "fetch.ps1" not in calls and "[fetch] skip: inputs unchanged" in lines
    calls, lines = osm_build(again(resort), NOW)                      # 15 days: fetched again, and built again
    assert "[fetch] run: 1 file(s) over their maximum age (osm/: 14 days)" in lines
    assert "fetch.ps1" in calls and "build_pack.py" in calls
    out = capsys.readouterr().out
    assert "1 file(s) over their maximum age (osm/: 14 days), fetched again: osm/ski.json" in out
    assert "fetched for an older manifest item" not in out
    index = F.load(resort.raw)
    assert index["osm/ski.json"]["fetched"] == F.stamp(NOW)
    assert index["dem1m/a.tif"]["fetched"] == F.stamp(days_ago(15))   # on disk, so not fetched again
    calls, _ = osm_build(again(resort), NOW)
    assert "fetch.ps1" not in calls and "build_pack.py" not in calls


def test_a_skipped_fetch_stage_gives_an_old_index_its_times_and_then_leaves_it_alone(resort):
    osm_build(resort, days_ago(30))
    path = os.path.join(resort.raw, F.INDEX)
    json.dump({p: e["key"] for p, e in F.load(resort.raw).items()}, open(path, "w"))     # the FEAT-346 form
    calls, _ = osm_build(again(resort), NOW)
    assert "fetch.ps1" not in calls and os.path.isfile(os.path.join(resort.raw, "osm", "ski.json"))
    assert {e["fetched"] for e in F.load(resort.raw).values()} == {F.stamp(NOW)}
    before = open(path, "rb").read()
    calls, _ = osm_build(again(resort), NOW + timedelta(days=1))   # a restored folder, built again: same bytes
    assert "fetch.ps1" not in calls and open(path, "rb").read() == before
