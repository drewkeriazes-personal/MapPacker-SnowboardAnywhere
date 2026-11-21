"""tools/ci/refresh_packs.py (FEAT-342): which published packs a refresh rebuilds, and which it leaves out and why."""
import io, json, os, subprocess, sys, zipfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools", "ci"))
import refresh_packs as rp  # noqa: E402
import release_zip as rz  # noqa: E402

BASE = "origin/main"


def config(resorts, slug, **cfg):
    d = resorts / slug
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{slug}.json").write_text(json.dumps({"slug": slug, **cfg}), encoding="utf-8")
    return d


def entry(slug, stamp="aaaa111", url=True):
    pack = {"pipeline": stamp, "bytes": 1000}
    if url:
        pack["url"] = f"https://x/{slug}.zip"
    return {"slug": slug, "name": slug.title(), "pack": pack}


def fake_git(changed: dict[str, list[str]], known=("aaaa111", "bbbb222")):
    """git with commits `known`; `git diff --name-only <stamp> base -- <paths>` answers the files in `changed` (path ->
    stamps it changed after) that fall under the pathspecs"""
    calls = []

    def git(*args, cwd=None):
        calls.append(args)
        if args[0] == "cat-file":
            ok = args[2].split("^")[0] in known
            return subprocess.CompletedProcess(args, 0 if ok else 1, "", "")
        if args[0] == "diff":
            stamp, specs = args[2], args[args.index("--") + 1:]
            inc = [s for s in specs if not s.startswith(":(")]
            exc = [s.split(")", 1)[1] for s in specs if s.startswith(":(exclude)")]
            files = [f for f, after in changed.items() if stamp in after
                     and any(f == s or f.startswith(s + "/") for s in inc)
                     and not any(f == s or f.startswith(s + "/") for s in exc) and not f.endswith(".md")]
            return subprocess.CompletedProcess(args, 0, "\n".join(files), "")
        raise AssertionError(args)
    git.calls = calls
    return git


def by_slug(rows):
    return {r["slug"]: r for r in rows}


def test_needs_updating_picks_the_packs_whose_build_inputs_changed(tmp_path):
    for s in ("alpha", "beta", "gamma", "delta"):
        config(tmp_path, s)
    cat = {"resorts": [entry("alpha"), entry("beta", "bbbb222"), entry("gamma", "dead999"), entry("delta")]}
    git = fake_git({"pipeline/build_pack.py": ["aaaa111"], "pipeline/tests/test_x.py": ["bbbb222"],
                    "pipeline/NOTES.md": ["bbbb222"]})
    rows = by_slug(rp.plan(cat, "needs updating", BASE, resorts=str(tmp_path), git=git, attract=None))
    assert rows["alpha"]["action"] == "start" and "pipeline/build_pack.py" in rows["alpha"]["detail"]
    assert rows["delta"]["action"] == "start"
    assert rows["beta"]["action"] == "up_to_date", "tests and Markdown are not build inputs"
    assert rows["gamma"]["action"] == "start" and "not in this repo's history" in rows["gamma"]["detail"]


def test_a_change_to_the_resort_or_a_source_it_builds_on_counts(tmp_path):
    config(tmp_path, "boston-mills")
    config(tmp_path, "mad-river", source_only=True)
    config(tmp_path, "ohio-hills", raw_from="boston-mills", relocate=[{"source": "mad-river"}])
    config(tmp_path, "other")
    cat = {"resorts": [entry("boston-mills"), entry("ohio-hills"), entry("other")]}
    git = fake_git({"resorts/mad-river/mad-river.json": ["aaaa111"]})
    rows = by_slug(rp.plan(cat, "needs updating", BASE, resorts=str(tmp_path), git=git, attract=None))
    assert rows["ohio-hills"]["action"] == "start"
    assert rows["boston-mills"]["action"] == rows["other"]["action"] == "up_to_date"
    git = fake_git({"manifests/boston-mills.json": ["aaaa111"]})
    rows = by_slug(rp.plan(cat, "needs updating", BASE, resorts=str(tmp_path), git=git, attract=None))
    assert rows["boston-mills"]["action"] == rows["ohio-hills"]["action"] == "start"
    assert rows["other"]["action"] == "up_to_date"


def test_all_starts_every_pack_it_can_without_asking_git(tmp_path):
    config(tmp_path, "alpha")
    git = fake_git({})
    rows = rp.plan({"resorts": [entry("alpha")]}, "all", BASE, resorts=str(tmp_path), git=git, attract=None)
    assert rows[0]["action"] == "start" and not git.calls


def test_left_out_packs_each_get_a_reason_code(tmp_path):
    config(tmp_path, "big")
    (tmp_path / "big" / "runner.json").write_text(json.dumps({"cloud": False, "reason": "too_big", "why": "30 GB"}))
    config(tmp_path, "menu")
    config(tmp_path, "plain")
    config(tmp_path, "nourl")
    config(tmp_path, "broken")
    config(tmp_path, "src", source_only=True)
    cat = {"resorts": [entry(s) for s in ("big", "menu", "plain", "src", "noconfig")] + [entry("nourl", url=False),
                                                                                         entry("broken")],
           "test": [entry("synth")]}

    def attract(url, size):
        if "broken" in url:
            raise OSError("HTTP 404")
        return {"generated": True, "stills": ["s"], "ghosts": []} if "menu" in url else {"generated": True,
                                                                                         "stills": [], "ghosts": []}
    rows = by_slug(rp.plan(cat, "all", BASE, resorts=str(tmp_path), git=fake_git({}), attract=attract))
    want = {"big": "too_big", "src": "no_config", "noconfig": "no_config",
            "nourl": "no_release", "broken": "attract_unread", "synth": "test_pack"}
    assert {s: r["reason"] for s, r in rows.items() if r["action"] == "left_out"} == want
    assert rows["plain"]["action"] == "start" and rows["plain"]["reason"] is None and not rows["plain"].get("note")
    # FEAT-345: a pack published with a menu still or takes is started; its build carries the riders over
    assert rows["menu"]["action"] == "start" and rows["menu"]["reason"] is None and rows["menu"]["gpu_still"] is True
    assert rows["menu"]["note"] == rp.GPU_STILL_NOTE and "still needs the PC" in rp.GPU_STILL_NOTE
    assert "still needs the PC" in rp.table(list(rows.values()), "all", "abc1234")
    assert "30 GB" in rows["big"]["detail"]
    assert set(want.values()) <= set(rp.REASONS)


def test_up_to_date_packs_are_not_downloaded(tmp_path):
    config(tmp_path, "alpha")
    seen = []
    rows = rp.plan({"resorts": [entry("alpha")]}, "needs updating", BASE, resorts=str(tmp_path), git=fake_git({}),
                   attract=lambda u, s: seen.append(u))
    assert rows[0]["action"] == "up_to_date" and not seen


@pytest.mark.parametrize("index, want", [
    (None, False), ({"generated": True, "stills": [], "ghosts": []}, False),
    ({"generated": True, "stills": ["a"]}, True), ({"generated": True, "ghosts": ["a-start-run-1.json"]}, True),
    ({"hand": True, "stills": ["a"]}, False),     # a hand-made menu is copied from resorts/<slug>/attract/ by any build
])
def test_needs_gpu_only_for_a_generated_menu_with_stills_or_ghosts(index, want):
    assert rp.needs_gpu(index) is want


def zip_bytes(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("meta.json", "{}")
        z.writestr("terrain/0_0.bin", os.urandom(50_000))
        for name, data in files.items():
            z.writestr(name, data)
    return buf.getvalue()


def range_server(data, log):
    class Resp(io.BytesIO):
        status = 206

    def opener(req, timeout=None):
        a, b = req.headers["Range"].removeprefix("bytes=").split("-")
        log.append((int(a), int(b)))
        return Resp(data[int(a):int(b) + 1])
    return opener


def test_published_attract_reads_one_file_by_ranges(monkeypatch):
    data = zip_bytes({"attract/index.json": json.dumps({"generated": True, "stills": ["x"]})})
    log = []
    monkeypatch.setattr(rz.urllib.request, "urlopen", range_server(data, log))
    assert rp.published_attract("https://x/a.zip", len(data)) == {"generated": True, "stills": ["x"]}
    assert sum(b - a + 1 for a, b in log) < len(data) / 2, "it read the directory and one file, not the zip"
    data = zip_bytes({})
    monkeypatch.setattr(rz.urllib.request, "urlopen", range_server(data, []))
    assert rp.published_attract("https://x/a.zip", len(data)) is None
    with pytest.raises(OSError):
        rp.published_attract("https://x/a.zip", 0)
    monkeypatch.setattr(rz.urllib.request, "urlopen", range_server(b"not a zip at all" * 10, []))
    with pytest.raises(OSError):
        rp.published_attract("https://x/a.zip", 160)


def test_main_starts_the_picked_packs_and_writes_the_summary_and_json(tmp_path, monkeypatch, capsys):
    cat = tmp_path / "catalog.json"
    cat.write_text(json.dumps({"resorts": [entry("a"), entry("b")], "test": [entry("synth")]}))
    rows = [{"slug": "a", "name": "A", "stamp": "x", "action": "start", "reason": None, "detail": ""},
            {"slug": "b", "name": "B", "stamp": "x", "action": "start", "reason": None, "detail": ""},
            {"slug": "synth", "name": "S", "stamp": "x", "action": "left_out", "reason": "test_pack", "detail": "t"}]
    monkeypatch.setattr(rp, "plan", lambda *a, **k: [dict(r) for r in rows])
    monkeypatch.setenv("GITHUB_REPOSITORY", "o/r")
    monkeypatch.setenv("GITHUB_RUN_ID", "77")
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    started = []

    def start(repo, slug, own):
        started.append((repo, slug, own))
        if slug == "b":
            raise RuntimeError("HTTP 422")
        return f"https://github.com/o/r/actions/runs/{len(started)}"
    out = tmp_path / "plan.json"
    code = rp.main(["--mode", "needs updating", "--catalog", str(cat), "--json", str(out), "--base", "HEAD"],
                   start=start)
    assert code == 1, "a failed start fails the run"
    assert started == [("o/r", "a", "77"), ("o/r", "b", "77")]
    doc = json.loads(out.read_text())
    assert [r["action"] for r in doc["packs"]] == ["start", "start_failed", "left_out"]
    assert doc["left_out"] == [doc["packs"][2]] and doc["left_out"][0]["reason"] == "test_pack"
    text = summary.read_text()
    assert "[run](https://github.com/o/r/actions/runs/1)" in text and "**start failed**" in text and "`test_pack`" in text


def test_list_only_starts_nothing(tmp_path, monkeypatch):
    cat = tmp_path / "catalog.json"
    cat.write_text(json.dumps({"resorts": []}))
    monkeypatch.setattr(rp, "plan", lambda *a, **k: [{"slug": "a", "name": "A", "stamp": "x", "action": "start",
                                                      "reason": None, "detail": ""}])
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    assert rp.main(["--mode", "list only", "--catalog", str(cat), "--base", "HEAD"], start=lambda *a: 1 / 0) == 0


def test_the_build_paths_skip_tests_and_docs_and_name_the_sources(tmp_path):
    config(tmp_path, "boston-mills")
    config(tmp_path, "ohio-hills", raw_from="boston-mills")
    specs = rp.build_paths("ohio-hills", str(tmp_path))
    assert specs[:3] == ["pipeline", ":(exclude)pipeline/tests", ":(exclude,glob)pipeline/**/*.md"]
    assert {"resorts/ohio-hills", "manifests/ohio-hills.json", "resorts/boston-mills",
            "manifests/boston-mills.json"} <= set(specs)


def test_the_real_catalog_plans_without_error():
    """every catalog pack gets a row (offline: --no-attract and mode all, so neither git history nor the network)"""
    with open(os.path.join(rp.ROOT, "catalog.json"), encoding="utf-8") as f:
        cat = json.load(f)
    rows = rp.plan(cat, "all", "HEAD", attract=None)
    assert len(rows) == len(cat["resorts"]) + len(cat.get("test") or [])
    assert all(r["action"] in ("start", "left_out") for r in rows)
    assert by_slug(rows)["vail"]["reason"] == "too_big"     # resorts/vail/runner.json


def test_list_only_shows_the_needs_updating_plan(tmp_path):
    config(tmp_path, "alpha")
    rows = rp.plan({"resorts": [entry("alpha")]}, "list only", BASE, resorts=str(tmp_path), git=fake_git({}),
                   attract=None)
    assert rows[0]["action"] == "up_to_date"
