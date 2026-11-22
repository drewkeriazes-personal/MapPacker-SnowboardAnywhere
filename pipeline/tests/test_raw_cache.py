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
    open(os.path.join(raw, "build_resort.json"), "w").write('{"fetch": "new"}')     # stage state: not data
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
