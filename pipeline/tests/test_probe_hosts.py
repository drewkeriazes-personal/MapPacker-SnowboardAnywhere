"""tools/ci/probe_hosts.py (FEAT-245): the data host probe, checked without the network."""
import json, os, sys
from urllib.parse import parse_qs, urlparse

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools", "ci"))
import probe_hosts as ph  # noqa: E402
import gen_manifest  # noqa: E402  (pipeline/ is on the path through probe_hosts)

TIFF = b"II*\x00" + b"\x00" * 60
WEBP = b"RIFF\x10\x00\x00\x00WEBPVP8 " + b"\x00" * 20


@pytest.fixture(autouse=True)
def no_build_slug(monkeypatch):
    """a local run: no "NAIP items of <slug>" row unless a test sets REBUILD or SLUG"""
    monkeypatch.delenv("REBUILD", raising=False)
    monkeypatch.delenv("SLUG", raising=False)


def test_checks():
    assert ph.tiff(200, TIFF)[0] and not ph.tiff(200, b"<html>error</html>")[0] and not ph.tiff(500, TIFF)[0]
    assert ph.webp(200, WEBP)[0] and not ph.webp(200, TIFF)[0]
    assert ph.range_ok(206, b"x")[0] and ph.range_ok(200, b"x")[0]
    assert not ph.range_ok(206, b"")[0] and not ph.range_ok(404, b"x")[0]
    ept = ph.json_with("bounds", "schema")
    assert ept(200, json.dumps({"bounds": [], "schema": []}).encode())[0]
    assert not ept(200, b'{"bounds": []}')[0] and not ept(200, b"not json")[0] and not ept(403, b"{}")[0]
    # LFPS: an unknown job id is HTTP 500 with JSON (seen 2026-11-12), and that means the service is up
    assert ph.any_json(500, b'{"message":"JobId not found.","success":false}')[0]
    assert not ph.any_json(200, b"<html>maintenance</html>")[0] and not ph.any_json(503, b"{}")[0]
    assert ph.overpass(200, b'{"version": 0.6, "elements": []}')[0]
    assert not ph.overpass(200, b"<?xml?><remark>runtime error</remark>")[0]   # 200 with an error body
    assert ph.cdx(200, b'[["urlkey"]]')[0] and not ph.cdx(200, b"<html>")[0]


def test_every_probe_has_a_url_and_a_check_and_only_grooming_is_optional():
    ps = ph.probes()
    assert all(p.url.startswith("https://") and callable(p.check) for p in ps)
    assert [p.host for p in ps if not p.required] == ["web.archive.org"]
    names = " ".join(p.name for p in ps)
    for host in ("ImageServer", "EPT", "Planetary Computer", "Mapterhorn", "Overpass", "LFPS", "WorldCover", "ETH",
                 "GNIS", "Census", "OpenSkiData"):
        assert host in names
    assert len([p for p in ps if p.host == "Overpass"]) == 3


def by_name(ps, *names):
    return [p for p in ps if p.name in names]


def test_a_host_with_mirrors_passes_when_one_mirror_passes():
    ps = [p for p in ph.probes() if p.host == "Overpass"]
    results = [(ps[0], False, "HTTP 504", 1.0), (ps[1], True, "ok", 1.0), (ps[2], False, "HTTP 504", 1.0)]
    assert ph.failed_hosts(results) == ([], [])
    assert "down (mirror ok)" in ph.table(results)
    results = [(p, False, "HTTP 504", 1.0) for p in ps]
    assert ph.failed_hosts(results) == (["Overpass"], [])


def fake(answers):
    """fetch(url, range) answering by a substring of the url; everything else answers like a healthy host"""
    def fetch(url, rng):
        for key, reply in answers.items():
            if key in url:
                return reply
        if "interpreter" in url:
            return 200, b'{"version": 0.6, "elements": []}'
        if "exportImage" in url or "/item/bbox/" in url:
            return 200, TIFF
        if url.endswith(".webp"):
            return 200, WEBP
        if "lfps" in url:
            return 400, b'{"message": "bad job"}'
        if "cdx" in url:
            return 200, b"[]"
        if rng:
            return 206, b"x" * 1024
        if "ept.json" in url:
            return 200, b'{"bounds": [], "schema": []}'
        if "tnmaccess" in url:
            return 200, b'{"items": []}'
        if "MapServer" in url:
            return 200, b'{"features": []}'
        if "/stac/v1/search" in url:
            ids = parse_qs(urlparse(url).query)["ids"][0].split(",")
            return 200, json.dumps({"type": "FeatureCollection", "features": [{"id": i} for i in ids]}).encode()
        if "collections/naip" in url:
            return 200, b'{"id": "naip", "extent": {}}'
        return 200, b"{}"
    return fetch


def test_main_passes_when_every_host_answers_and_writes_the_summary(tmp_path, monkeypatch, capsys):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    assert ph.main([], fetch=fake({})) == 0
    text = summary.read_text(encoding="utf-8")
    assert "| host | result |" in text and "FAIL" not in text
    assert "every host answered" in capsys.readouterr().out


def test_main_fails_on_a_required_host_after_the_inline_retries(monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.setattr(ph.time, "sleep", lambda s: None)
    calls = []

    def fetch(url, rng):
        if "lfps" in url:
            calls.append(url)
            return 0, b"curl: (28) Operation timed out"
        return fake({})(url, rng)
    assert ph.main([], fetch=fetch) == 1
    assert len(calls) == 3                     # retry.json probe.tries
    assert "unreachable: lfps.usgs.gov" in capsys.readouterr().out


def test_the_archive_only_warns(monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.setattr(ph.time, "sleep", lambda s: None)
    assert ph.main([], fetch=fake({"cdx": (503, b"down")})) == 0
    assert "warning: web.archive.org" in capsys.readouterr().out


def test_only_picks_probes_by_name_or_host(monkeypatch):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    seen = []

    def fetch(url, rng):
        seen.append(url)
        return fake({})(url, rng)
    assert ph.main(["--only", "overpass"], fetch=fetch) == 0
    assert len(seen) == 1 and "interpreter" in seen[0]     # the mirrors only when it fails
    assert ph.main(["--only", "no-such-host"], fetch=fetch) == 2


def test_a_mirror_is_not_tried_once_its_host_answered():
    seen = []

    def fetch(url, rng):
        seen.append(url)
        return 200, b'{"version": 0.6, "elements": []}' if "interpreter" in url else b"{}"
    over = [p for p in ph.probes() if p.host == "Overpass"]
    assert len(over) == 3
    ph.main(["--only", "Overpass"], fetch=fetch)
    assert seen == [over[0].url]


def test_tuning_raises_one_hosts_tries_within_the_caps(monkeypatch, tmp_path, capsys):
    """FEAT-314: host-tuning.json from the metrics branch; a bad file is the defaults"""
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.setattr(ph.time, "sleep", lambda s: None)
    t = tmp_path / "host-tuning.json"
    t.write_text(json.dumps({"lfps.usgs.gov": {"timeout": 9999, "tries": 99}}))
    assert ph.load_tuning(str(t)) == {"lfps.usgs.gov": {"timeout": 180, "tries": 4}}
    assert ph.load_tuning(str(tmp_path / "missing.json")) == {} and ph.load_tuning(None) == {}
    (tmp_path / "bad.json").write_text("not json")
    assert ph.load_tuning(str(tmp_path / "bad.json")) == {}
    calls = []

    def fetch(url, rng):
        if "lfps" in url:
            calls.append(url)
            return 0, b"curl: (28) Operation timed out"
        return fake({})(url, rng)
    assert ph.main(["--tuning", str(t)], fetch=fetch) == 1
    assert len(calls) == 4 and "tuned: lfps.usgs.gov 180 s, 4 tries" in capsys.readouterr().out


def test_a_one_off_connect_failure_recovers_inline_and_is_logged(monkeypatch, tmp_path, capsys):
    """FEAT-314 refinement: the Deer Valley case (Geofabrik curl 7 once) passes in the same attempt"""
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    log = tmp_path / "inline.jsonl"
    monkeypatch.setenv("SBA_RETRY_LOG", str(log))
    waits = []
    monkeypatch.setattr(ph.time, "sleep", waits.append)
    calls = []

    def fetch(url, rng):
        if "geofabrik" in url:
            calls.append(url)
            if len(calls) == 1:
                return 0, b"curl: (7) Failed to connect to download.geofabrik.de port 443"
        return fake({})(url, rng)
    assert ph.main([], fetch=fetch) == 0
    assert len(calls) == 2 and len(waits) == 1 and 8 <= waits[0] <= 12        # 10 s, jitter 20%
    rows = {d["host"]: d for d in map(json.loads, log.read_text().splitlines())}
    assert rows["download.geofabrik.de"] == {"tool": "probe", "host": "download.geofabrik.de", "calls": 1,
                                             "retried": 1, "recovered": 1, "failed": 0}
    assert rows["lfps.usgs.gov"]["retried"] == 0
    assert "Recovered inline: download.geofabrik.de" in capsys.readouterr().out


def test_a_4xx_is_not_retried_and_retry_after_is_respected(monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    waits = []
    monkeypatch.setattr(ph.time, "sleep", waits.append)
    calls = []

    def fetch(url, rng):
        if "geofabrik" in url:
            calls.append(url)
            return 404, b"not found"
        if "tiles.openskimap" in url:
            calls.append(url)
            return (429, b"slow down", 90) if calls.count(url) == 1 else (206, b"x")
        return fake({})(url, rng)
    assert ph.main([], fetch=fetch) == 1
    assert len(calls) == 3 and len(waits) == 1 and waits[0] >= 90 * 0.8     # Retry-After 90 over the 10 s wait
    assert "HTTP 404 (a 4xx: not retried)" in capsys.readouterr().out


def test_the_retry_budget_caps_the_waits_of_a_whole_run(monkeypatch):
    monkeypatch.setattr(ph.time, "sleep", lambda s: None)
    p = ph.Probe("x", "x.org", "https://x.org/", ph.http_ok)
    budget = [15]
    ok, detail, _, k = ph.run_probe(p, lambda u, r: (503, b""), budget=budget)
    assert not ok and k == 2 and "retry budget used up" in detail and budget[0] < 15    # 10 s spent, 30 s refused


# ---------------------------------------------------------------- BUG-169


def test_naip_url_is_the_bbox_route_with_each_side_capped_at_2048():
    u = gen_manifest.naip_url((100, 200, 1899, 2891), 1799, 2691, "co_m_x", "EPSG:26913")
    assert u.startswith("https://planetarycomputer.microsoft.com/api/data/v1/item/bbox/100,200,1899,2891/1799x2048.tif?")
    assert "/item/crop/" not in u
    q = parse_qs(urlparse(u).query)
    assert q["collection"] == ["naip"] and q["item"] == ["co_m_x"] and q["asset_bidx"] == ["image|1,2,3,4"]
    assert q["coord_crs"] == q["dst_crs"] == ["EPSG:26913"] and q["resampling"] == ["average"]
    assert "/2048x2048.tif" in gen_manifest.naip_url((0, 0, 4000, 2500), 4000, 2500, "i", "EPSG:26913")
    assert "/2048x64.tif" in gen_manifest.naip_url((0, 0, 4000, 64), 4000, 64, "i", "EPSG:26913")


def test_the_manifest_asks_for_the_capped_size_and_keeps_the_meta():
    with open(ph.paths.config_path("vail"), encoding="utf-8") as f:
        cfg = json.load(f)
    naip = [i for i in gen_manifest.manifest_items(cfg) if i["path"].startswith("naip1m/")]
    assert naip and gen_manifest.MANIFEST_VERSION == 3
    for it in naip:
        w, h = it["meta"]["size"]
        bx0, by0, bx1, by1 = it["meta"]["bbox"]
        assert (w, h) == (bx1 - bx0, by1 - by0)          # the meta keeps the full 1 m size (FEAT-346's index keys)
        assert f"/item/bbox/{bx0},{by0},{bx1},{by1}/{min(w, 2048)}x{min(h, 2048)}.tif?" in it["url"]
    assert any(max(i["meta"]["size"]) > 2048 for i in naip)    # Vail has crops the cap cuts


def test_the_probe_uses_the_manifests_naip_route():
    p = next(p for p in ph.probes() if p.name == "Planetary Computer NAIP crop")
    assert p.url.startswith(gen_manifest.NAIP_BBOX_URL) and "/64x64.tif?" in p.url


def test_each_row_stands_for_itself_on_a_shared_host(monkeypatch, capsys):
    """the NAIP route failing is a failure though the STAC row on the same host passed; so are WESM next to GNIS
    (prd-tnm.s3) and the Census population file next to the gazetteer (www2.census.gov)"""
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.setattr(ph.time, "sleep", lambda s: None)
    for key, host in (("/item/bbox/", "planetarycomputer.microsoft.com"), ("wesm", "prd-tnm.s3.amazonaws.com"),
                      ("popest", "www2.census.gov")):
        row = next(p for p in ph.probes() if p.host == host and key.lower() in p.url.lower())
        assert ph.main([], fetch=fake({row.url: (404, b'{"detail":"Not Found"}')})) == 1, key
        out = capsys.readouterr().out
        assert f"unreachable: {host}" in out and f"FAIL {row.name}: HTTP 404" in out, key
        assert [ln for ln in out.splitlines() if "not tried (host ok)" in ln and "Overpass" not in ln] == [], key


def test_build_slug_reads_the_run_inputs_like_build_pack_ci():
    assert ph.build_slug({}) == ""
    assert ph.build_slug({"REBUILD": "heavenly", "SLUG": ""}) == "heavenly"
    assert ph.build_slug({"REBUILD": "(new resort: type the slug below)", "SLUG": " mt-new "}) == "mt-new"
    assert ph.build_slug({"SLUG": "bad slug; rm"}) == ""


def write_cfg(d, slug, items, **kw):
    os.makedirs(d / slug, exist_ok=True)
    cfg = {"slug": slug, "naip": {"item_bboxes_ll": {i: [0, 0, 1, 1] for i in items}}, **kw}
    (d / slug / f"{slug}.json").write_text(json.dumps(cfg), encoding="utf-8")


def test_naip_items_of_a_config_and_what_it_builds_on(tmp_path):
    write_cfg(tmp_path, "a", ["a1", "a2"], raw_from="b", relocate=[{"source": "c"}, {"dx": 1}])
    write_cfg(tmp_path, "b", ["b1", "a1"])
    write_cfg(tmp_path, "c", [], relocate=[{"source": "a"}])
    assert ph.naip_items("a", str(tmp_path)) == ["a1", "a2", "b1"]
    assert ph.naip_items("new-resort", str(tmp_path)) == []                 # no config yet
    assert ph.build_naip_items({"SLUG": "a"}, str(tmp_path)) == ("a", ["a1", "a2", "b1"])
    assert ph.build_naip_items({"SLUG": "new-resort"}, str(tmp_path)) is None
    assert ph.build_naip_items({}, str(tmp_path)) is None
    write_cfg(tmp_path, "abroad", [])
    assert ph.build_naip_items({"SLUG": "abroad"}, str(tmp_path)) is None   # no NAIP outside the US


def test_naip_items_check_names_the_items_gone_and_the_fix():
    url = ph.stac_items_url(["x1", "x2", "x3"])
    q = parse_qs(urlparse(url).query)
    assert url.startswith(ph.STAC_SEARCH + "?") and q["ids"] == ["x1,x2,x3"] and q["collections"] == ["naip"]
    check = ph.naip_items_check("heavenly", ["x1", "x2", "x3"])
    ok, detail = check(200, json.dumps({"features": [{"id": "x2"}]}).encode())
    assert not ok and "x1, x3" in detail and "resort.py plan heavenly" in detail and "x2" not in detail.split(":")[1]
    assert check(200, json.dumps({"features": [{"id": i} for i in ("x1", "x2", "x3")]}).encode())[0]
    assert not check(200, b"<html>")[0] and not check(503, b"{}")[0]


def test_a_build_run_probes_its_resorts_naip_items(monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.setattr(ph.time, "sleep", lambda s: None)
    monkeypatch.setenv("REBUILD", "vail")
    rows = [p.name for p in ph.probes()]
    assert rows[rows.index("Planetary Computer NAIP crop") + 1] == "NAIP items of vail"
    assert ph.main(["--only", "NAIP"], fetch=fake({})) == 0
    gone = next(iter(json.load(open(ph.paths.config_path("vail"), encoding="utf-8"))["naip"]["item_bboxes_ll"]))

    def fetch(url, rng):
        if "/stac/v1/search" in url:
            ids = [i for i in parse_qs(urlparse(url).query)["ids"][0].split(",") if i != gone]
            return 200, json.dumps({"features": [{"id": i} for i in ids]}).encode()
        return fake({})(url, rng)
    assert ph.main(["--only", "NAIP"], fetch=fetch) == 1
    out = capsys.readouterr().out
    assert gone in out and "resort.py plan vail" in out and "unreachable: planetarycomputer.microsoft.com" in out


def covers_file(tmp_path, covers=("bm", "mad"), keep=("tiles.openskimap.org",)):
    p = tmp_path / "raw-cache-covers.json"
    p.write_text(json.dumps({"covers": list(covers), "keep": list(keep)}), encoding="utf-8")
    return str(p)


DOWN = {"interpreter": (0, b"curl: (7) Failed to connect"), "geofabrik": (0, b"curl: (7) Failed to connect")}


def test_a_covering_raw_cache_lets_the_fetch_hosts_warn(tmp_path, monkeypatch, capsys):
    """FEAT-347: Overpass and Geofabrik down, and the raw cache covers every folder: the probe passes and says why"""
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setattr(ph.time, "sleep", lambda s: None)
    assert ph.main(["--raw-cache", covers_file(tmp_path)], fetch=fake(DOWN)) == 0
    out, text = capsys.readouterr().out, summary.read_text(encoding="utf-8")
    assert "Raw cache covers bm, mad" in out and "Raw cache covers bm, mad" in text
    (line,) = [ln for ln in text.splitlines() if ln.startswith("Raw cache covers")]
    assert "download.geofabrik.de" in line and "Overpass" in line and "tiles.openskimap.org" not in line
    assert "warning: Overpass, download.geofabrik.de unreachable (not needed: the raw cache covers the build)" in out


def test_the_hosts_a_covered_build_still_calls_stay_required(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.setattr(ph.time, "sleep", lambda s: None)
    down = {"openskimap": (0, b"curl: (7) Failed to connect")}
    assert ph.main(["--raw-cache", covers_file(tmp_path)], fetch=fake(down)) == 1
    assert "unreachable: tiles.openskimap.org" in capsys.readouterr().out


@pytest.mark.parametrize("content", [None, "not json", '{"covers": []}', '{"covers": [], "keep": []}'])
def test_no_covering_file_means_the_probe_as_before(tmp_path, monkeypatch, capsys, content):
    """no file (a miss, a changed manifest, fresh_data: raw_cache.py covered writes none), a bad one, or one that
    covers nothing: every host is required"""
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.setattr(ph.time, "sleep", lambda s: None)
    path = tmp_path / "raw-cache-covers.json"
    if content is not None:
        path.write_text(content, encoding="utf-8")
    assert ph.main(["--raw-cache", str(path)], fetch=fake(DOWN)) == 1
    out = capsys.readouterr().out
    assert "unreachable: Overpass, download.geofabrik.de" in out and "Raw cache covers" not in out


# ---------------------------------------------------------------- BUG-170


PLAN_ONLY = {"TNM Access products", "3DEP work units (WESM.csv)", "Entwine boundaries", "Planetary Computer STAC naip",
             "Mapterhorn attribution", "Geofabrik index"}


def test_the_hosts_only_a_new_resorts_plan_calls_are_marked():
    """resort.py resolve/plan read these (Geofabrik at plan's geofabrik_for, Entwine's index, TNM's DEM tiles, WESM,
    the STAC search, Mapterhorn's attribution); a rebuild builds from its committed config and manifest"""
    assert {p.name for p in ph.probes() if p.plan_only} == PLAN_ONLY


def test_a_rebuild_lets_the_plan_only_hosts_warn(monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.setattr(ph.time, "sleep", lambda s: None)
    monkeypatch.setenv("REBUILD", "vail")
    down = {"geofabrik": (0, b"curl: (7) Failed to connect"), "entwine": (0, b"curl: (7) Failed to connect")}
    assert ph.main([], fetch=fake(down)) == 0
    out = capsys.readouterr().out
    assert "A rebuild of vail: " in out and "Geofabrik index" in out and "plan calls them" in out
    assert "download.geofabrik.de, usgs.entwine.io unreachable (only a new resort's plan calls them)" in out


def test_a_new_resort_still_needs_the_plan_only_hosts(monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.setattr(ph.time, "sleep", lambda s: None)
    monkeypatch.setenv("REBUILD", "(new resort: type the slug below)")
    monkeypatch.setenv("SLUG", "brand-new-resort")
    assert ph.main([], fetch=fake({"geofabrik": (0, b"curl: (7) Failed to connect")})) == 1
    out = capsys.readouterr().out
    assert "unreachable: download.geofabrik.de" in out and "A rebuild of" not in out


def test_is_rebuild_needs_a_config(tmp_path):
    write_cfg(tmp_path, "old", [])
    assert ph.is_rebuild({"REBUILD": "old"}, str(tmp_path)) == "old"
    assert ph.is_rebuild({"SLUG": "new-one"}, str(tmp_path)) == ""
    assert ph.is_rebuild({}, str(tmp_path)) == ""
