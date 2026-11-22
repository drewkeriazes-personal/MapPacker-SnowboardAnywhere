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


def test_a_failed_fetch_records_nothing_it_does_not_have(resort):
    with pytest.raises(B.Failed):
        go(resort, Fake(resort, fetch_code=2))
    assert F.load(resort.raw) == {}


def test_a_failed_fetch_records_the_files_it_has_and_is_not_complete(resort):
    """FEAT-349: what came is in the index, so the raw cache saves it and a retry fetches only the rest; a complete
    marker left from an older manifest's fetch goes"""
    go(resort, Fake(resort))
    put(resort.raw, {"path": "dem1m/a.tif"})              # the Fake fetch writes dem1m/a; the manifest names a.tif
    have = F.load(resort.raw)
    assert list(have) == ["dem1m/a.tif"] and os.path.isfile(os.path.join(resort.raw, F.COMPLETE))
    man = json.load(open(resort.man_path))
    man["items"].append({"url": "https://x.org/b.tif", "path": "dem1m/b.tif"})       # a new item, then a failure
    json.dump(man, open(resort.man_path, "w"))
    r = B.Resort("demo", resort.raw, resort.out, resort.resorts, resort.manifests)
    with pytest.raises(B.Failed):
        B.fetch_run(r, B.Context(runner=Fake(r, fetch_code=2)))
    assert F.load(resort.raw) == have                   # a.tif kept with its entry, b.tif (never fetched) has none
    assert not os.path.exists(os.path.join(resort.raw, F.COMPLETE))
