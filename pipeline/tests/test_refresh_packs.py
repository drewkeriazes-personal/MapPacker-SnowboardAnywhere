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
    want = {"src": "no_config", "noconfig": "no_config",
            "nourl": "no_release", "broken": "attract_unread", "synth": "test_pack"}
    assert {s: r["reason"] for s, r in rows.items() if r["action"] == "left_out"} == want
    assert rows["plain"]["action"] == "start" and rows["plain"]["reason"] is None and not rows["plain"].get("note")
    # FEAT-345: a pack published with a menu still or takes is started; its build carries the riders over
    assert rows["menu"]["action"] == "start" and rows["menu"]["reason"] is None and rows["menu"]["gpu_still"] is True
    assert rows["menu"]["note"] == rp.GPU_STILL_NOTE and "still needs the PC" in rp.GPU_STILL_NOTE
    assert "still needs the PC" in rp.table(list(rows.values()), "all", "abc1234")
    assert rows["big"]["action"] == "pc" and rows["big"]["reason"] == "too_big" and not rows["big"].get("gpu_still")
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
    assert all(r["action"] in ("start", "left_out", "pc") for r in rows)
    assert by_slug(rows)["vail"]["action"] == "pc"     # resorts/vail/runner.json


def test_list_only_shows_the_needs_updating_plan(tmp_path):
    config(tmp_path, "alpha")
    rows = rp.plan({"resorts": [entry("alpha")]}, "list only", BASE, resorts=str(tmp_path), git=fake_git({}),
                   attract=None)
    assert rows[0]["action"] == "up_to_date"


# ------------------------------------------------------------------------------------------------ Drew's PC (too_big)

def big(tmp_path, slug="big"):
    config(tmp_path, slug)
    (tmp_path / slug / "runner.json").write_text(json.dumps({"cloud": False, "reason": "too_big"}))


def test_a_too_big_pack_goes_to_the_pc_by_the_same_pick(tmp_path):
    big(tmp_path)
    big(tmp_path, "fresh")
    cat = {"resorts": [entry("big"), entry("fresh", "bbbb222")]}
    git = fake_git({"pipeline/build_pack.py": ["aaaa111"]})
    seen = []
    rows = by_slug(rp.plan(cat, "needs updating", BASE, resorts=str(tmp_path), git=git,
                           attract=lambda u, s: seen.append(u)))
    assert rows["big"]["action"] == "pc" and rows["fresh"]["action"] == "up_to_date"
    assert not seen, "the PC renders the menu itself: no read of the published one"
    rows = by_slug(rp.plan(cat, "all", BASE, resorts=str(tmp_path), git=git, attract=None))
    assert rows["big"]["action"] == rows["fresh"]["action"] == "pc"
    assert "would go to Drew's PC" in rp.table(list(rows.values()), "list only", "abc1234")


def test_main_hands_the_pc_packs_to_the_pc_job_and_starts_only_the_cloud_ones(tmp_path, monkeypatch):
    cat = tmp_path / "catalog.json"
    cat.write_text(json.dumps({"resorts": []}))
    monkeypatch.setattr(rp, "plan", lambda *a, **k: [
        {"slug": "a", "name": "A", "stamp": "x", "action": "start", "reason": None, "detail": ""},
        {"slug": "vail", "name": "Vail", "stamp": "x", "action": "pc", "reason": "too_big", "detail": ""}])
    monkeypatch.setenv("GITHUB_REPOSITORY", "o/r")
    monkeypatch.setenv("GITHUB_RUN_ID", "77")
    out = tmp_path / "out"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    started = []
    assert rp.main(["--catalog", str(cat), "--base", "HEAD"], start=lambda *a: started.append(a) or "u") == 0
    assert started == [("o/r", "a", "77")]
    assert out.read_text() == 'pc=["vail"]\n'


def pc_env(monkeypatch, tmp_path, slugs, token="tok"):
    monkeypatch.setattr(rp.paths, "runner_path", lambda s, r=None: str(tmp_path / s / "runner.json"))
    monkeypatch.setenv("GITHUB_REPOSITORY", "o/r")
    monkeypatch.setenv("GITHUB_RUN_ID", "77")
    monkeypatch.setenv("PC_SLUGS", json.dumps(slugs))
    monkeypatch.setenv("GH_TOKEN", token)
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    return summary


def test_start_pc_starts_build_on_pc_with_the_refresh_run_and_links_it(tmp_path, monkeypatch):
    big(tmp_path, "vail")
    config(tmp_path, "small")
    summary = pc_env(monkeypatch, tmp_path, ["vail", "small", "../x"])
    started = []

    def start(repo, slug, own, build_on):
        started.append((repo, slug, own, build_on))
        return "https://github.com/o/r/actions/runs/5"
    out = tmp_path / "pc.json"
    code = rp.main(["--start-pc", "--json", str(out)], start=start, status=lambda repo: "online")
    assert started == [("o/r", "vail", "77", "pc")], "only a pack runner.json sends to the PC"
    assert code == 1, "a refused slug fails the job"
    text = summary.read_text()
    assert "building on Drew's PC ([run](https://github.com/o/r/actions/runs/5))" in text and "online" in text
    assert {r["slug"]: r["action"] for r in json.loads(out.read_text())["packs"]} == {
        "vail": "building", "small": "refused", "../x": "refused"}


@pytest.mark.parametrize("status, word", [("offline", "queued: PC runner offline"),
                                          (None, "building on Drew's PC")])
def test_an_offline_or_unreadable_runner_still_queues_the_build(tmp_path, monkeypatch, status, word):
    big(tmp_path, "vail")
    summary = pc_env(monkeypatch, tmp_path, ["vail"])
    assert rp.main(["--start-pc"], start=lambda *a: "https://r/1", status=lambda repo: status) == 0
    text = summary.read_text()
    assert f"{word} ([run](https://r/1))" in text
    assert ("**offline**" in text) if status else ("Administration: read" in text)


def test_a_missing_token_says_so_and_gives_the_hand_command(tmp_path, monkeypatch):
    big(tmp_path, "vail")
    summary = pc_env(monkeypatch, tmp_path, ["vail"], token="")
    assert rp.main(["--start-pc"], start=lambda *a: 1 / 0, status=lambda repo: 1 / 0) == 1
    text = summary.read_text()
    assert "PC_DISPATCH_TOKEN is not set" in text and "**not started**" in text
    assert "`gh workflow run build-pack.yml -f slug=vail -f build_on=pc`" in text


def test_a_refused_token_says_so_and_gives_the_hand_command(tmp_path, monkeypatch):
    big(tmp_path, "vail")
    summary = pc_env(monkeypatch, tmp_path, ["vail"])

    def start(*a):
        raise RuntimeError("gh: Bad credentials (HTTP 401)")
    assert rp.main(["--start-pc"], start=start, status=lambda repo: None) == 1
    text = summary.read_text()
    assert "GitHub refused" in text and "expired, revoked" in text
    assert "still needs a hand build: `gh workflow run build-pack.yml -f slug=vail -f build_on=pc`" in text


def test_dispatch_sends_build_on_only_for_the_pc(monkeypatch):
    cmds = []

    def run(cmd, **k):
        cmds.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, '{"html_url": "https://r/9"}', "")
    monkeypatch.setattr(rp.subprocess, "run", run)
    assert rp.dispatch("o/r", "vail", "77", "pc") == "https://r/9"
    assert rp.dispatch("o/r", "a", "77") == "https://r/9"
    assert "inputs[build_on]=pc" in cmds[0] and "inputs[slug]=vail" in cmds[0] and "inputs[refresh_run]=77" in cmds[0]
    assert not any("build_on" in c for c in cmds[1])
