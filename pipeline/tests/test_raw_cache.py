"""FEAT-346: the free runner's raw-data cache (tools/ci/raw_cache.py), against a fake draft release in memory."""
import io
import json
import os
import sys
import tarfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools", "ci"))
import raw_cache as C  # noqa: E402


class Release:
    """the draft releases: answers raw_cache's gh calls and downloads from `assets`, and records the calls"""

    def __init__(self):
        self.releases, self.calls = {}, []      # tag -> {asset name: bytes}

    def gh(self, *args):
        self.calls.append(args)
        verb, tag = args[1], args[2]
        assets = self.releases.get(tag)
        if verb == "create":
            self.releases[tag] = {}
            return ""
        if assets is None:
            raise RuntimeError("release not found")
        if verb == "view":
            return json.dumps(sorted(assets)) if "assets" in args else "{}"
        if verb == "download":
            return assets[args[args.index("-p") + 1]].decode()
        if verb == "upload":
            with open(args[3], "rb") as f:
                assets[os.path.basename(args[3])] = f.read()
            return ""
        if verb == "delete-asset":
            del assets[args[3]]
            return ""
        raise AssertionError(args)

    def open_part(self, folder, name):
        data = self.releases[C.tag(folder)][name]

        class Proc:
            stdout = io.BytesIO(data)

            def wait(self):
                return 0
        return Proc()


@pytest.fixture
def rel(monkeypatch, tmp_path):
    r = Release()
    monkeypatch.setattr(C, "gh", r.gh)
    monkeypatch.setattr(C, "open_part", r.open_part)
    monkeypatch.setattr(C, "PART", 4096)          # several parts from a small folder
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    return r


def raw_folder(root, name="demo", big=10_000):
    raw = os.path.join(root, name)
    for rel, data in {"dem1m/a.tif": os.urandom(big), "osm/ski.json": b'{"elements": [1]}',
                      "fetch_index.json": b'{"dem1m/a.tif": "k1"}', "FETCH_COMPLETE.txt": b"complete",
                      "build_resort.json": b"{}", "fetch_log.txt": b"log", "naip1m/b.tif.part": b"half"}.items():
        path = os.path.join(raw, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "wb").write(data)
    return raw


def tree(raw):
    return {os.path.relpath(os.path.join(d, n), raw).replace(os.sep, "/"): open(os.path.join(d, n), "rb").read()
            for d, _, names in os.walk(raw) for n in names}


def test_save_then_restore_gives_the_folder_back(rel, tmp_path):
    raw = raw_folder(str(tmp_path / "a"))
    assert C.save_one("demo", raw).startswith("saved")
    cache = json.loads(rel.releases["raw/demo"]["cache.json"])
    assert len(cache["parts"]) > 1 and all(p["size"] <= 4096 for p in cache["parts"])
    out = str(tmp_path / "b" / "demo")
    assert C.restore_one("demo", out).startswith("restored")
    want = {k: v for k, v in tree(raw).items() if k not in ("fetch_log.txt", "naip1m/b.tif.part")}
    assert tree(out) == want                                     # no log, no partial download


def test_the_same_data_uploads_nothing(rel, tmp_path):
    raw = raw_folder(str(tmp_path))
    C.save_one("demo", raw)
    before = len(rel.calls)
    open(os.path.join(raw, "build_resort.json"), "w").write('{"build": "new"}')     # a later stage's state: not data
    open(os.path.join(raw, "fetch_log.txt"), "w").write("another run")
    assert C.save_one("demo", raw).startswith("skip: the cache already holds this data")
    assert not any(c[1] == "upload" for c in rel.calls[before:])


def test_new_data_replaces_the_old_parts(rel, tmp_path):
    raw = raw_folder(str(tmp_path))
    C.save_one("demo", raw)
    old = {p["name"] for p in json.loads(rel.releases["raw/demo"]["cache.json"])["parts"]}
    open(os.path.join(raw, "fetch_index.json"), "w").write('{"dem1m/a.tif": "k2"}')
    C.save_one("demo", raw)
    new = {p["name"] for p in json.loads(rel.releases["raw/demo"]["cache.json"])["parts"]}
    assert new and not old & new
    assert set(rel.releases["raw/demo"]) == new | {"cache.json"}
    uploads = [os.path.basename(c[3]) for c in rel.calls if c[1] == "upload"]
    assert uploads[-1] == "cache.json", "cache.json goes last: a save that dies halfway leaves the old set named"


def test_a_save_leaves_another_saves_parts_alone(rel, tmp_path):
    raw = raw_folder(str(tmp_path))
    rel.releases["raw/demo"] = {"other.tar.000": b"a concurrent save's part"}
    C.save_one("demo", raw)
    assert "other.tar.000" in rel.releases["raw/demo"]


def test_a_corrupt_part_empties_the_folder(rel, tmp_path):
    C.save_one("demo", raw_folder(str(tmp_path / "a")))
    assets = rel.releases["raw/demo"]
    last = json.loads(assets["cache.json"])["parts"][-1]["name"]     # the tar's end padding: only the hash sees it
    assets[last] = assets[last][:-1] + bytes([assets[last][-1] ^ 1])
    out = str(tmp_path / "b" / "demo")
    with pytest.raises(RuntimeError, match="sha256"):
        C.restore_one("demo", out)
    assert not os.path.exists(out)


def test_a_tar_that_climbs_out_of_the_folder_is_refused(rel, tmp_path):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        info = tarfile.TarInfo("../escaped.txt")
        info.size = 1
        tar.addfile(info, io.BytesIO(b"x"))
    data = buf.getvalue()
    import hashlib
    rel.releases["raw/demo"] = {"k.tar.000": data, "cache.json": json.dumps(
        {"key": "k", "parts": [{"name": "k.tar.000", "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}]}
    ).encode()}
    out = str(tmp_path / "root" / "demo")
    with pytest.raises(tarfile.FilterError):
        C.restore_one("demo", out)
    assert not os.path.exists(tmp_path / "root" / "escaped.txt") and not os.path.exists(out)


def test_restore_skips_a_folder_that_has_data_and_misses_without_a_cache(rel, tmp_path):
    raw = raw_folder(str(tmp_path))
    assert C.restore_one("demo", raw) == "skip: the folder already has data"
    assert C.restore_one("demo", str(tmp_path / "new")) == "miss: no cache yet"


def test_save_skips_a_folder_whose_fetch_did_not_finish(rel, tmp_path):
    raw = raw_folder(str(tmp_path))
    os.remove(os.path.join(raw, "FETCH_COMPLETE.txt"))
    assert C.save_one("demo", raw).startswith("skip: no finished fetch")
    assert rel.releases == {}


@pytest.fixture
def run_env(monkeypatch, tmp_path):
    monkeypatch.setenv("SBA_RAW_ROOT", str(tmp_path / "raw"))
    monkeypatch.setenv("REBUILD", "demo")
    monkeypatch.setattr(C.build_pack_ci, "from_env", lambda: {"slug": "ohio", "deps": ["bm", "mad"]})
    monkeypatch.setattr(C.build_pack_ci, "data_slug", lambda s: ({"ohio": "bm"}.get(s, s), {}))
    seen = []
    monkeypatch.setattr(C, "restore_one", lambda folder, raw: seen.append(folder) or "miss: no cache yet")
    return seen


def test_the_run_restores_every_folder_the_build_reads_once(run_env):
    assert C.main(["restore"]) == 0
    assert run_env == ["bm", "mad"]                          # ohio builds on bm's raw folder (raw_from)


def test_fresh_data_skips_the_restore(run_env, monkeypatch):
    monkeypatch.setenv("FRESH_DATA", "true")
    assert C.main(["restore"]) == 0
    assert run_env == []


def test_a_cache_failure_never_fails_the_build(run_env, monkeypatch, capsys):
    def boom(folder, raw):
        raise RuntimeError("gh is down")
    monkeypatch.setattr(C, "save_one", boom)
    assert C.main(["save"]) == 0
    assert "::warning::raw cache save bm: gh is down" in capsys.readouterr().out


# ------------------------------------------------------------------------------------------------ FEAT-347

DATA = ("nodes", "manifest", "fetch", "landfire", "grooming")


def test_save_records_the_data_stages_and_a_new_fingerprint_saves_again(rel, tmp_path):
    """cache.json's `stages` are the folder's data-stage fingerprints (fetch: the manifest the fetch used), and they
    are in the key, so the build_resort.json a restore puts back is always the one cache.json names"""
    raw = raw_folder(str(tmp_path))
    state = {**{s: f"{s}-1" for s in DATA}, "build": "b1"}
    open(os.path.join(raw, "build_resort.json"), "w").write(json.dumps(state))
    C.save_one("demo", raw)
    cache = json.loads(rel.releases["raw/demo"]["cache.json"])
    assert cache["stages"] == {s: f"{s}-1" for s in DATA}
    open(os.path.join(raw, "build_resort.json"), "w").write(json.dumps({**state, "fetch": "fetch-2"}))
    assert C.save_one("demo", raw).startswith("saved")
    assert json.loads(rel.releases["raw/demo"]["cache.json"])["stages"]["fetch"] == "fetch-2"


@pytest.fixture
def main_checkout(tmp_path, monkeypatch):
    """a resort `demo` on "main": its config and manifest in temp folders, and the cache.json a save of a fetch of
    exactly them writes"""
    import build_resort, gen_manifest
    resorts, manifests = tmp_path / "resorts", tmp_path / "manifests"
    (resorts / "demo").mkdir(parents=True)
    manifests.mkdir()
    cfg = {"name": "Demo", "crs": "EPSG:32613", "utm_bbox": [0, 0, 1000, 1000], "lonlat_bbox": [-106, 39, -105.9, 39.1],
           "terrain_status_url": "https://example.com/status"}
    (resorts / "demo" / "demo.json").write_text(json.dumps(cfg), encoding="utf-8")
    man = {"manifestVersion": gen_manifest.MANIFEST_VERSION, "items": [{"url": "https://x.org/a.tif", "path": "dem1m/a.tif"}]}
    (manifests / "demo.json").write_text(json.dumps(man), encoding="utf-8")
    monkeypatch.setenv("SBA_RAW_ROOT", str(tmp_path / "raw"))
    r = build_resort.Resort("demo", str(tmp_path / "raw" / "demo"), str(tmp_path / "packs" / "demo"), str(resorts),
                            str(manifests))
    cache = {"key": "k", "parts": [], "stages": {s: build_resort.STAGE_FN[s][0](r) for s in DATA}}

    def check(c=cache):
        return C.uncovered("demo", c, str(resorts), str(manifests))
    return check, cache, resorts / "demo" / "demo.json", manifests / "demo.json"


def test_a_cache_of_the_same_manifest_covers_the_build(main_checkout):
    check, *_ = main_checkout
    assert check() is None


def test_a_changed_manifest_is_not_covered(main_checkout):
    check, _, _, man = main_checkout
    d = json.loads(man.read_text(encoding="utf-8"))
    d["items"].append({"url": "https://x.org/b.tif", "path": "dem1m/b.tif"})
    man.write_text(json.dumps(d), encoding="utf-8")
    assert check() == "the manifest changed"


def test_a_changed_config_or_an_old_manifest_is_not_covered(main_checkout):
    check, _, cfg, man = main_checkout
    d = json.loads(man.read_text(encoding="utf-8"))
    man.write_text(json.dumps({**d, "manifestVersion": -1}), encoding="utf-8")   # the build would make it again
    assert check() == "the manifest stage would run again"
    man.write_text(json.dumps(d), encoding="utf-8")
    c = json.loads(cfg.read_text(encoding="utf-8"))
    cfg.write_text(json.dumps({**c, "name": "Demo 2"}), encoding="utf-8")
    assert check() == "the manifest stage's inputs changed"


def test_no_cache_an_old_cache_or_a_new_resort_is_not_covered(main_checkout, tmp_path):
    check, cache, *_ = main_checkout
    assert check(None) == "no cache yet"
    assert check({"key": "k", "parts": []}) == "the cache has no nodes fingerprint"     # saved before FEAT-347
    assert C.uncovered("new-one", cache, str(tmp_path / "resorts")) == "no config"


@pytest.fixture
def covered_env(monkeypatch, tmp_path):
    for k in ("FRESH_DATA", "BUILD_ON", "GITHUB_STEP_SUMMARY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(C.build_pack_ci, "from_env", lambda: {"slug": "ohio", "deps": ["bm", "mad"], "mode": "rebuild"})
    monkeypatch.setattr(C.build_pack_ci, "data_slug", lambda s: ({"ohio": "bm"}.get(s, s), {}))
    caches = {"bm": {"key": "1"}, "mad": {"key": "2"}}
    monkeypatch.setattr(C, "read_cache", lambda folder: caches[folder])
    gaps = {}
    monkeypatch.setattr(C, "uncovered", lambda folder, cache: gaps.get(folder))
    out = tmp_path / "covers.json"
    out.write_text("stale", encoding="utf-8")         # a file from before is never left behind
    return out, gaps


def test_covered_writes_the_file_only_when_every_folder_is_covered(covered_env, capsys):
    out, gaps = covered_env
    assert C.main(["covered", "--out", str(out)]) == 0
    assert json.loads(out.read_text(encoding="utf-8")) == {"covers": ["bm", "mad"], "keep": ["tiles.openskimap.org"]}
    assert "Raw cache covers bm, mad" in capsys.readouterr().out
    gaps["mad"] = "the manifest changed"
    assert C.main(["covered", "--out", str(out)]) == 0
    assert not out.exists()
    assert "does not cover mad (the manifest changed)" in capsys.readouterr().out


@pytest.mark.parametrize("env,want", [({"FRESH_DATA": "true"}, "fresh data asked for"),
                                      ({"BUILD_ON": "pc"}, "Drew's PC")])
def test_fresh_data_or_the_pc_is_never_covered(covered_env, monkeypatch, capsys, env, want):
    out, _ = covered_env
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    assert C.main(["covered", "--out", str(out)]) == 0
    assert not out.exists() and want in capsys.readouterr().out


def test_a_new_resort_or_any_error_is_never_covered(covered_env, monkeypatch, capsys):
    out, _ = covered_env
    monkeypatch.setattr(C.build_pack_ci, "from_env", lambda: {"slug": "new", "deps": [], "mode": "new"})
    assert C.main(["covered", "--out", str(out)]) == 0
    assert not out.exists() and "a new resort has none" in capsys.readouterr().out

    monkeypatch.setattr(C.build_pack_ci, "from_env", lambda: {"slug": "ohio", "deps": ["bm", "mad"], "mode": "rebuild"})

    def boom(folder):
        raise RuntimeError("gh is down")
    monkeypatch.setattr(C, "read_cache", boom)
    assert C.main(["covered", "--out", str(out)]) == 0
    assert not out.exists() and "not read: gh is down" in capsys.readouterr().out
