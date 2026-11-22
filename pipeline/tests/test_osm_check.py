"""FEAT-348: OpenStreetMap is fetched again when an Overpass change check finds edits since its fetch, or once it is
90 days old; the check, or a failed refetch, never fails a build that has a cached copy."""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools", "ci"))
import build_resort as B  # noqa: E402
import fetch_index as F  # noqa: E402
import osm_check as O  # noqa: E402
import raw_cache  # noqa: E402
from test_build_resort import Fake, resort  # noqa: E402,F401  (the build_resort fixture)
from test_fetch_index import NAIP, TILE, put  # noqa: E402

NOW = datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc)
BB = "41.2458829,-81.5845512,41.3030709,-81.5332085"
# gen_manifest.py's own Overpass queries (its ov() and peaks_far), as it writes them
SKI_Q = ('[out:json][timeout:180][maxsize:536870912];(way["piste:type"](' + BB + ');relation["piste:type"](' + BB
         + ');way["landuse"="winter_sports"](' + BB + '););out geom;')
PEAKS_Q = '[out:json][timeout:300][maxsize:536870912];node["natural"="peak"]["ele"](' + BB + ');out;'
HOSTS = ["https://overpass-api.de/api/interpreter", "https://overpass.private.coffee/api/interpreter",
         "https://lz4.overpass-api.de/api/interpreter"]


def overpass_item(name, q):
    enc = quote(q, safe="")
    return {"url": f"{HOSTS[0]}?data={enc}", "path": f"osm/{name}.json", "alts": [f"{h}?data={enc}" for h in HOSTS[1:]]}


OSM = overpass_item("ski", SKI_Q)
PEAKS = overpass_item("peaks_far", PEAKS_Q)


def days_ago(n):
    return NOW - timedelta(days=n)


def answer(*totals):
    return json.dumps({"version": 0.6, "elements": [
        {"type": "count", "id": 0, "tags": {"nodes": "0", "ways": str(n), "relations": "0", "total": str(n)}}
        for n in totals]}).encode()


# ------------------------------------------------------------------------------------------------ the query

def test_the_check_query_is_each_items_statements_since_its_fetch_with_a_count():
    q = O.check_query([(O.query_of(OSM), "2026-11-08T10:00:00Z"), (O.query_of(PEAKS), "2026-11-01T00:00:00Z")], 45)
    new, old = '(newer:"2026-11-08T10:00:00Z")', '(newer:"2026-11-01T00:00:00Z")'
    assert q == ('[out:json][timeout:45];'
                 f'(way["piste:type"]({BB}){new};relation["piste:type"]({BB}){new};'
                 f'way["landuse"="winter_sports"]({BB}){new};);out count;'
                 f'(node["natural"="peak"]["ele"]({BB}){old};);out count;')
    assert O.query_of({"url": HOSTS[0], "path": "osm/x.json", "body": "data=" + quote(PEAKS_Q, safe="")}) == PEAKS_Q


def test_the_real_manifests_queries_all_rewrite():
    """every Overpass query gen_manifest.py wrote for a committed resort can be checked"""
    man = os.path.join(os.path.dirname(__file__), "..", "..", "manifests", "boston-mills.json")
    if not os.path.isfile(man):
        pytest.skip("no committed manifest")
    items = [i for i in json.load(open(man, encoding="utf-8"))["items"] if i["path"].startswith(O.PREFIX)]
    q = O.check_query([(O.query_of(i), "2026-11-08T10:00:00Z") for i in items], 45)
    assert len(items) == 5 and q.count("out count;") == 5 and "geom" not in q and "maxsize" not in q
    assert q.count('(newer:"2026-11-08T10:00:00Z")') == sum(len(O.statements(O.query_of(i))) for i in items)


def test_a_query_the_check_cannot_filter_is_a_failed_check():
    with pytest.raises(O.CheckFailed):
        O.statements('[out:json];way["a"](1,2,3,4)->.a;out;')
    with pytest.raises(O.CheckFailed):
        O.statements('[out:json];(way["a"](1,2,3,4);')
    with pytest.raises(O.CheckFailed):
        O.check([{"url": HOSTS[0] + "?x=1", "path": "osm/x.json"}], {"osm/x.json": "t"}, sender=None)


# ------------------------------------------------------------------------------------------------ the request

def test_the_check_tries_the_fetchs_hosts_in_order_and_reads_one_count_per_item():
    tried = []

    def sender(base, query, timeout):
        tried.append(base)
        if base == HOSTS[0]:
            raise OSError("HTTP Error 502")
        return answer(0, 3)
    since = {OSM["path"]: "2026-11-08T10:00:00Z", PEAKS["path"]: "2026-11-08T10:00:00Z"}
    assert O.check([OSM, PEAKS], since, sender) == {"osm/ski.json": 0, "osm/peaks_far.json": 3}
    assert tried == HOSTS[:2]


@pytest.mark.parametrize("reply", [b"<html>busy</html>", answer(0),
                                   json.dumps({"elements": [], "remark": "runtime error: timed out"}).encode()])
def test_an_unreadable_answer_from_every_host_is_a_failed_check(reply):
    since = {OSM["path"]: "t", PEAKS["path"]: "t"}
    with pytest.raises(O.CheckFailed, match="lz4.overpass-api.de"):
        O.check([OSM, PEAKS], since, lambda b, q, t: reply)


def test_the_check_stays_within_its_time():
    t, given = [0.0], []

    def sender(base, query, timeout):
        given.append(timeout)
        t[0] += timeout                                   # every host hangs for all the time it is given
        raise TimeoutError("timed out")
    with pytest.raises(O.CheckFailed):
        O.check([OSM], {OSM["path"]: "t"}, sender, budget=60, clock=lambda: t[0])
    assert t[0] <= 60 and given == [20, 20, 20]           # a host that hangs leaves time for the next


# ------------------------------------------------------------------------------------------------ the index

def test_osm_has_a_90_day_backstop_and_the_other_layers_none(tmp_path):
    raw = str(tmp_path)
    osm, naip = put(raw, OSM, "old"), put(raw, NAIP)
    F.record(raw, [OSM, NAIP], [OSM["path"], NAIP["path"]], days_ago(91))
    assert F.max_age(OSM["path"]) == 90 and F.max_age(NAIP["path"]) is None
    assert F.over_age(raw, [OSM, NAIP], days_ago(2)) == []
    assert F.over_age(raw, [OSM, NAIP], NOW) == [OSM["path"]]
    assert F.prune(raw, [OSM, NAIP], NOW) == [OSM["path"]]
    assert not os.path.exists(osm) and open(osm + F.KEEP).read() == "old" and os.path.isfile(naip)
    assert F.restore_kept(raw, [OSM, NAIP]) == [OSM["path"]] and open(osm).read() == "old"


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
    open(os.path.join(raw, "osm", "ski.json" + F.KEEP), "w").write("old")         # a kept copy is never saved
    assert "osm/ski.json.keep" not in raw_cache.saved_files(raw)
    assert raw_cache.data_key(raw, raw_cache.saved_files(raw)) == key
    F.record(raw, [NAIP, TILE, OSM], [OSM["path"]], NOW)                          # OSM fetched again
    assert raw_cache.data_key(raw, raw_cache.saved_files(raw)) != key             # the next save uploads it


def test_the_failed_items_are_read_from_the_last_run_in_the_log(tmp_path):
    first = ("09:00:00  Manifest demo: 3 items -> /raw/demo\n"
             "09:00:09  Failed items (re-run this script to retry them):\n09:00:09    dem1m/a.tif\n")
    last = ("10:00:00  Manifest demo: 3 items -> /raw/demo\n10:00:01    FAILED osm/ski.json: HTTP 504\n"
            "10:00:02  Finished: 0 downloaded (0 MB), 2 skipped, 1 failed\n"
            "10:00:02  Failed items (re-run this script to retry them):\n10:00:02    osm/ski.json\n")
    open(tmp_path / "fetch_log.txt", "w").write(first + last)
    assert B.failed_items(str(tmp_path)) == ["osm/ski.json"]
    open(tmp_path / "fetch_log.txt", "w").write(first + "10:00:00  Manifest demo: 3 items -> /raw/demo\n")
    assert B.failed_items(str(tmp_path)) is None


# ------------------------------------------------------------------------------------------------ the fetch stage
# the build_resort fixture, with an OSM item in the Fake manifest and a fake Overpass

class Overpass:
    def __init__(self, *totals, fail=False):
        self.totals, self.fail, self.calls = totals, fail, 0

    def __call__(self, base, query, timeout):
        self.calls += 1
        if self.fail:
            raise OSError("HTTP Error 502: Bad Gateway")
        return answer(*self.totals)


def no_overpass(base, query, timeout):
    pytest.fail("the change check sent a request")


def osm_build(r, clock, overpass=no_overpass, fetch_fails=None):
    """one build_resort run; `fetch_fails`: the paths fetch.ps1 lists as failed (exit 2)"""
    fake = Fake(r, fetch_code=2 if fetch_fails else 0)

    def run(cmd, cwd=None, env=None):
        script = os.path.basename(cmd[cmd.index("-File") + 1] if "-File" in cmd else cmd[1])
        if script == "fetch.ps1" and fetch_fails:
            with open(os.path.join(r.raw, "fetch_log.txt"), "a") as f:
                f.write("10:00:00  Manifest demo: 2 items -> x\n10:00:01  Failed items (re-run this script to retry "
                        "them):\n" + "".join(f"10:00:01    {p}\n" for p in fetch_fails))
        code = fake(cmd, cwd, env)
        if script == "gen_manifest.py":
            m = json.load(open(r.man_path))
            m["items"].append(OSM)
            json.dump(m, open(r.man_path, "w"))
        if script == "fetch.ps1" and not code:
            for item in json.load(open(r.man_path))["items"]:         # what a real fetch leaves: every item
                if not os.path.exists(os.path.join(r.raw, item["path"])):
                    put(r.raw, item, "fetched")
        return code
    lines = []
    B.build(r, B.Context(runner=run, email="me@example.com", clock=lambda: clock, overpass=overpass),
            out=lines.append)
    return fake.calls, lines


def again(r):
    return B.Resort("demo", r.raw, r.out, r.resorts, r.manifests)


def ski_time(r):
    return F.load(r.raw)["osm/ski.json"]["fetched"]


def test_unchanged_osm_is_kept_and_the_pack_is_not_built_again(resort, capsys):
    osm_build(resort, days_ago(3))
    index = open(os.path.join(resort.raw, F.INDEX), "rb").read()
    op = Overpass(0)
    calls, lines = osm_build(again(resort), NOW, op)
    assert op.calls == 1                                             # one check per build
    assert "fetch.ps1" not in calls and "build_pack.py" not in calls and "[fetch] skip: inputs unchanged" in lines
    assert "osm: unchanged since 2026-11-19" in capsys.readouterr().out
    assert open(os.path.join(resort.raw, F.INDEX), "rb").read() == index


def test_edited_osm_is_fetched_again_and_the_pack_built_again(resort, capsys):
    osm_build(resort, days_ago(3))
    op = Overpass(12)
    calls, lines = osm_build(again(resort), NOW, op)
    assert op.calls == 1 and "fetch.ps1" in calls and "build_pack.py" in calls   # decide and fetch_run share it
    assert "[fetch] run: OpenStreetMap to fetch again (osm/ski.json)" in lines
    out = capsys.readouterr().out
    assert "osm: 12 elements edited since 2026-11-19, fetched again (osm/ski.json)" in out
    assert "fetched for an older manifest item" not in out
    assert ski_time(resort) == F.stamp(NOW) and F.load(resort.raw)["dem1m/a.tif"]["fetched"] == F.stamp(days_ago(3))
    assert not os.path.exists(os.path.join(resort.raw, "osm", "ski.json" + F.KEEP))
    calls, _ = osm_build(again(resort), NOW, Overpass(0))
    assert "fetch.ps1" not in calls and "build_pack.py" not in calls


def test_osm_past_the_backstop_is_fetched_again_without_a_check(resort, capsys):
    osm_build(resort, days_ago(91))
    calls, _ = osm_build(again(resort), NOW)                          # no_overpass: no request
    assert "fetch.ps1" in calls and "build_pack.py" in calls and ski_time(resort) == F.stamp(NOW)
    assert "osm: last fetched 2026-08-23, over 90 days, fetched again (osm/ski.json)" in capsys.readouterr().out


def test_a_failed_check_keeps_the_cached_osm_and_warns(resort, capsys, monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    osm_build(resort, days_ago(3))
    calls, _ = osm_build(again(resort), NOW, Overpass(fail=True))
    assert "fetch.ps1" not in calls and "build_pack.py" not in calls and ski_time(resort) == F.stamp(days_ago(3))
    out = capsys.readouterr().out
    assert "::warning::osm: check failed, kept the cached copy (overpass-api.de: HTTP Error 502" in out


def test_a_failed_refetch_puts_the_cached_copy_back_and_the_build_goes_on(resort, capsys):
    osm_build(resort, days_ago(3))
    ski = os.path.join(resort.raw, "osm", "ski.json")
    cached = json.dumps({"elements": [{"id": 7}]})
    open(ski, "w").write(cached)
    calls, _ = osm_build(again(resort), NOW, Overpass(5), fetch_fails=["osm/ski.json"])
    assert "fetch.ps1" in calls and "build_pack.py" not in calls     # the data didn't change: the pack is current
    assert open(ski).read() == cached and not os.path.exists(ski + F.KEEP)
    assert ski_time(resort) == F.stamp(days_ago(3))                   # so the next build checks again
    assert "osm: fetch again failed, kept the cached copy (osm/ski.json)" in capsys.readouterr().out


def test_a_failed_fetch_of_anything_else_fails_as_before(resort):
    osm_build(resort, days_ago(3))
    ski = os.path.join(resort.raw, "osm", "ski.json")
    with pytest.raises(B.Failed, match="some downloads failed"):
        osm_build(again(resort), NOW, Overpass(5), fetch_fails=["osm/ski.json", "dem1m/b.tif"])
    assert os.path.isfile(ski) and not os.path.exists(ski + F.KEEP)   # the copy is back for the next run


def test_a_failed_first_fetch_of_osm_with_no_copy_fails(resort):
    with pytest.raises(B.Failed, match="some downloads failed"):
        osm_build(resort, NOW, fetch_fails=["osm/ski.json"])


def test_an_old_index_is_not_checked_but_gets_its_times_and_then_keeps_its_bytes(resort):
    osm_build(resort, days_ago(30))
    path = os.path.join(resort.raw, F.INDEX)
    json.dump({p: e["key"] for p, e in F.load(resort.raw).items()}, open(path, "w"))     # the FEAT-346 form
    calls, _ = osm_build(again(resort), NOW)                          # no_overpass: an unknown time isn't checked
    assert "fetch.ps1" not in calls and os.path.isfile(os.path.join(resort.raw, "osm", "ski.json"))
    assert {e["fetched"] for e in F.load(resort.raw).values()} == {F.stamp(NOW)}
    before = open(path, "rb").read()
    calls, _ = osm_build(again(resort), NOW + timedelta(days=1), Overpass(0))   # a restored folder, built again
    assert "fetch.ps1" not in calls and open(path, "rb").read() == before
