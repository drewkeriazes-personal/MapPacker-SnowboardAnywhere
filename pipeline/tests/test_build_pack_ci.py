"""FEAT-245: tools/ci/build_pack_ci.py, the build-pack workflow's steps."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools", "ci"))
import build_pack_ci as ci  # noqa: E402


def config(resorts, slug, **cfg):
    d = os.path.join(resorts, slug)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, f"{slug}.json"), "w", encoding="utf-8") as f:
        json.dump({"name": slug.title(), **cfg}, f)


def test_a_new_slug_needs_a_name_and_an_osm_id(tmp_path):
    with pytest.raises(ci.Refused, match="new resort"):
        ci.check_inputs("Boston Mills", "", "boston-mills", "", tmp_path)
    got = ci.check_inputs(" Boston Mills ", "way/123", "boston-mills", "uid-1", tmp_path)
    assert got["mode"] == "new" and got["name"] == "Boston Mills" and got["osm_id"] == "way/123"
    assert got["deps"] == [] and got["tier"] == "gold"
    assert ci.check_inputs("Beaver Creek", "skimap/497", "beaver-creek", "", tmp_path)["osm_id"] == "skimap/497"
    for bad in ("skimap/0", "skimap.org/497", "node/5", "skimap/497; rm -rf /"):        # FEAT-286 shapes only
        with pytest.raises(ci.Refused, match="not an OSM or Skimap.org id"):
            ci.check_inputs("Beaver Creek", bad, "beaver-creek", "", tmp_path)


def test_an_existing_slug_is_a_rebuild_from_its_config(tmp_path):
    config(tmp_path, "vail", tier="gold", name="Vail")
    got = ci.check_inputs("", "", "vail", "", tmp_path)
    assert got["mode"] == "rebuild" and got["name"] == "Vail"


def test_the_workflow_call_reads_the_repo_resorts_folder(monkeypatch):
    """BUG-116: the workflow calls from_env(), no folder given; None must mean resorts/, not crash"""
    monkeypatch.setenv("SLUG", "vail")
    for k in ("NAME", "OSM_ID", "REQUESTED_BY"):
        monkeypatch.delenv(k, raising=False)
    assert ci.from_env()["mode"] == "rebuild"
    got = ci.check_inputs("Heavenly Mountain Resort", "relation/12152028", "no-such-resort-bug-116", "")
    assert got["mode"] == "new"
    assert sorted(ci.deps("ohio-hills")) == ["boston-mills", "mad-river-mountain"]


@pytest.mark.parametrize("slug,osm,who", [
    ("Vail", "", ""), ("vail;rm -rf /", "", ""), ("-vail", "", ""), ("a" * 61, "", ""),
    ("new", "way/12 $(id)", ""), ("new", "node/12", ""), ("new", "0", ""),
    ("new", "12", "uid with spaces"), ("new", "12", "x" * 129),
])
def test_inputs_outside_their_shapes_are_refused(tmp_path, slug, osm, who):
    with pytest.raises(ci.Refused):
        ci.check_inputs("Name", osm, slug, who, tmp_path)


@pytest.mark.parametrize("name", ["Vail\nrm", "--force", "-x"])
def test_a_name_with_control_characters_or_a_leading_dash_is_refused(tmp_path, name):
    with pytest.raises(ci.Refused):
        ci.check_inputs(name, "12", "new", "", tmp_path)


def test_a_relocate_source_is_not_built_on_its_own(tmp_path):
    config(tmp_path, "mad-river-mountain", source_only=True)
    with pytest.raises(ci.Refused, match="relocate source"):
        ci.check_inputs("", "", "mad-river-mountain", "", tmp_path)


def test_deps_fetch_raw_from_and_relocate_sources_first(tmp_path):
    config(tmp_path, "mad-river-mountain", source_only=True)
    config(tmp_path, "boston-mills", relocate=[{"source": "mad-river-mountain"}, {"offset": [1, 2]}])
    config(tmp_path, "ohio-hills", raw_from="boston-mills", relocate=[{"source": "mad-river-mountain"}])
    assert ci.deps("boston-mills", tmp_path) == ["mad-river-mountain"]
    assert ci.deps("ohio-hills", tmp_path) == ["mad-river-mountain", "boston-mills"]
    cfg = ci.check_inputs("", "", "ohio-hills", "", tmp_path)
    fetch = ci.stage_commands("fetch", cfg)
    assert [c[2] for c in fetch] == ["mad-river-mountain", "boston-mills", "ohio-hills"]
    assert all(c[-2:] == ["--stop-after", "grooming"] for c in fetch)


def test_resolve_uses_the_osm_id_alone_and_stops_after_the_plan(tmp_path):
    cfg = ci.check_inputs("Boston Mills", "way/42", "boston-mills", "", tmp_path)
    (cmd,) = ci.stage_commands("resolve", cfg)
    assert cmd[1].endswith("resort.py") and cmd[2] == "add" and cmd[-2:] == ["--", "Boston Mills"]
    assert cmd[cmd.index("--osm") + 1] == "way/42" and cmd[cmd.index("--slug") + 1] == "boston-mills"
    assert "--alone" in cmd and cmd[cmd.index("--stop-after") + 1] == "plan"
    config(tmp_path, "vail")
    assert ci.stage_commands("resolve", ci.check_inputs("", "", "vail", "", tmp_path)) == []


def test_publish_passes_the_run_and_the_requester(tmp_path):
    config(tmp_path, "vail", tier="silver")
    cfg = {**ci.check_inputs("", "", "vail", "uid-1", tmp_path), "run_url": "https://github.com/o/r/actions/runs/9"}
    (cmd,) = ci.stage_commands("publish", cfg)
    assert cmd[1].endswith("publish_pack.py") and cmd[2].endswith(os.path.join("packs", "vail"))
    assert cmd[cmd.index("--tier") + 1] == "silver"
    assert cmd[cmd.index("--run-url") + 1] == "https://github.com/o/r/actions/runs/9"
    assert "--requested-by=uid-1" in cmd


def test_a_requester_starting_with_a_dash_is_refused(tmp_path):
    with pytest.raises(ci.Refused):
        ci.check_inputs("Name", "12", "new", "-abc", tmp_path)


def test_the_name_is_escaped_in_the_summary():
    assert ci.md("A|B <b>*x*</b> [l](u)") == r"A\|B \<b\>\*x\*\</b\> \[l\](u)"


@pytest.mark.parametrize("text,want", [
    ("vail is unchanged since v4 (content ab): nothing to publish", "unchanged since v4: nothing published"),
    ("https://github.com/o/r/pull/7 is open with this content: nothing to publish",
     "already in https://github.com/o/r/pull/7: nothing published"),
    ("opened https://github.com/o/r/pull/8 (draft release vail/v5): ...", "opened https://github.com/o/r/pull/8"),
])
def test_the_summary_says_what_publish_did(text, want):
    assert ci.publish_result(text) == want


def test_a_stage_writes_a_summary_line_and_stops_on_failure(tmp_path, monkeypatch):
    config(tmp_path, "vail")
    summ = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summ))
    monkeypatch.setenv("SLUG", "vail")
    monkeypatch.setattr(ci, "from_env", lambda: ci.check_inputs("", "", "vail", "", tmp_path))
    calls = []
    assert ci.main(["build"], runner=lambda cmd: (calls.append(cmd), (0, "ok"))[1],
                   carry=lambda *a, **k: {"carried": False, "why": "test"}) == 0
    assert ci.main(["report"], runner=lambda cmd: (3, "boom")) == 3
    lines = summ.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("| build | done; no menu carried (test) |") and lines[1].startswith("| report | **failed** (exit 3) |")
    assert len(calls) == 1



def test_the_fetch_summary_says_what_the_osm_check_found(tmp_path, monkeypatch):
    """FEAT-348"""
    config(tmp_path, "vail")
    summ = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summ))
    monkeypatch.setattr(ci, "from_env", lambda: ci.check_inputs("", "", "vail", "", tmp_path))
    log = ("[fetch] run: OpenStreetMap to fetch again (osm/ski.json)\n"
           "  osm: 12 elements edited since 2026-11-08, fetched again (osm/ski.json)\n"
           "::warning::osm: fetch again failed, kept the cached copy (osm/ski.json)\n")
    assert ci.main(["fetch"], runner=lambda cmd: (0, log)) == 0
    assert ("| fetch | done; osm: 12 elements edited since 2026-11-08, fetched again (osm/ski.json); osm: fetch "
            "again failed, kept the cached copy (osm/ski.json) |") in summ.read_text(encoding="utf-8")


def test_refused_inputs_fail_every_stage(tmp_path, monkeypatch):
    summ = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summ))
    for k, v in {"SLUG": "Bad Slug", "NAME": "", "OSM_ID": "", "REQUESTED_BY": ""}.items():
        monkeypatch.setenv(k, v)
    assert ci.main(["check"], runner=lambda cmd: pytest.fail("ran a command")) == 1
    assert "Refused" in summ.read_text(encoding="utf-8")


def test_inputs_writes_the_mode_for_the_cache_step(tmp_path, monkeypatch):
    out = tmp_path / "out.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.setattr(ci, "from_env", lambda: ci.check_inputs("Boston Mills", "42", "boston-mills", "", tmp_path))
    assert ci.main(["inputs"]) == 0
    assert out.read_text(encoding="utf-8").splitlines() == ["mode=new", "slug=boston-mills"]


# ------------------------------------------------------------------------------------------------ FEAT-297, BUG-124

def test_a_pack_picked_in_the_rebuild_list_is_the_slug(tmp_path):
    config(tmp_path, "vail", tier="gold", name="Vail")
    got = ci.check_inputs("", "", "", "", tmp_path, rebuild="vail")
    assert got["mode"] == "rebuild" and got["slug"] == "vail" and got["name"] == "Vail"
    assert ci.check_inputs("", "", "vail", "", tmp_path, rebuild="vail")["slug"] == "vail"     # typed the same
    with pytest.raises(ci.Refused, match="picked vail but the slug typed is heavenly"):
        ci.check_inputs("", "", "heavenly", "", tmp_path, rebuild="vail")
    with pytest.raises(ci.Refused, match="no config"):
        ci.check_inputs("", "", "", "", tmp_path, rebuild="gone")
    with pytest.raises(ci.Refused, match="not a pack slug"):
        ci.check_inputs("", "", "", "", tmp_path, rebuild="vail; rm -rf /")


def test_the_new_resort_entry_falls_back_to_the_typed_slug(tmp_path):
    new = ci.rebuild_choices.NEW
    got = ci.check_inputs("Boston Mills", "way/123", "boston-mills", "", tmp_path, rebuild=new)
    assert got["mode"] == "new" and got["slug"] == "boston-mills"
    with pytest.raises(ci.Refused, match="pick one in the rebuild list, or type a slug"):
        ci.check_inputs("", "", "", "", tmp_path, rebuild=new)


def test_the_env_carries_the_pick(monkeypatch):
    monkeypatch.setenv("REBUILD", "vail")
    for k in ("SLUG", "NAME", "OSM_ID", "REQUESTED_BY"):
        monkeypatch.delenv(k, raising=False)
    assert ci.from_env()["slug"] == "vail"                     # the repo's own resorts/vail/vail.json


def test_the_report_step_runs_the_published_stage_first():
    """BUG-124: published (FEAT-293) sits between index and report; build stops at index"""
    cfg = {"slug": "vail", "mode": "rebuild", "deps": [], "tier": "gold"}
    assert ci.stage_commands("build", cfg)[0][-4:] == ["--from", "build", "--stop-after", "index"]
    assert ci.stage_commands("report", cfg)[0][-4:] == ["--from", "published", "--stop-after", "report"]


# ------------------------------------------------------------------------------------------------ FEAT-344: Drew's PC

DISPATCH = {"BUILD_ON": "pc", "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REF": "refs/heads/main",
            "GITHUB_ACTOR": "drew", "GITHUB_TRIGGERING_ACTOR": "drew"}


def test_cloud_is_the_default_and_anything_else_is_refused():
    assert ci.where({}, set()) == "cloud" and ci.where({"BUILD_ON": "cloud"}, set()) == "cloud"
    with pytest.raises(ci.Refused, match="not one of cloud, pc"):
        ci.where({"BUILD_ON": "self-hosted"}, {"drew"})


def test_the_pc_takes_only_a_dispatch_on_main_by_a_maintainer():
    assert ci.where(DISPATCH, {"drew"}) == "pc"
    for change, why in (({"GITHUB_EVENT_NAME": "pull_request"}, "not workflow_dispatch"),
                        ({"GITHUB_EVENT_NAME": "pull_request_target"}, "not workflow_dispatch"),
                        ({"GITHUB_REF": "refs/heads/issue-1-x"}, "not refs/heads/main"),
                        ({"GITHUB_REF": "refs/pull/5/merge"}, "not refs/heads/main"),
                        ({"GITHUB_ACTOR": "someone", "GITHUB_TRIGGERING_ACTOR": "someone"}, "someone is not in"),
                        ({"GITHUB_TRIGGERING_ACTOR": "someone"}, r"someone \(who re-ran it\)")):
        with pytest.raises(ci.Refused, match=why):
            ci.where({**DISPATCH, **change}, {"drew"})
    with pytest.raises(ci.Refused, match="nobody is not in"):
        ci.where({k: v for k, v in DISPATCH.items() if not k.endswith("ACTOR")}, {"drew"})
    # FEAT-314: build-pack-retry.yml re-runs a maintainer's run as the workflow bot
    assert ci.where({**DISPATCH, "GITHUB_TRIGGERING_ACTOR": "github-actions[bot]"}, {"drew"}) == "pc"


def test_the_repo_maintainers_list_is_read():
    assert "drewkeriazes" in ci.maintainers()


def test_where_writes_the_runner_output_and_refuses_with_a_summary(tmp_path, monkeypatch):
    out, summ = tmp_path / "out.txt", tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summ))
    monkeypatch.setattr(ci, "from_env", lambda: ci.check_inputs("", "", "vail", "", tmp_path))
    config(tmp_path, "vail")
    monkeypatch.setattr(ci, "maintainers", lambda: {"drew"})
    for k, v in DISPATCH.items():
        monkeypatch.setenv(k, v)
    assert ci.main(["where"]) == 0 and out.read_text(encoding="utf-8").splitlines() == ["runner=pc"]
    monkeypatch.setenv("GITHUB_REF", "refs/heads/branch")
    assert ci.main(["where"]) == 1 and "Refused" in summ.read_text(encoding="utf-8")


def raw(root, slug, *folders):
    for f in folders:
        os.makedirs(os.path.join(root, slug, f), exist_ok=True)


def test_the_raw_root_holding_the_resort_is_picked(tmp_path):
    res, a, b = tmp_path / "resorts", str(tmp_path / "a"), str(tmp_path / "b")
    config(res, "vail", lidar={"x": 1}, naip={"x": 1})
    config(res, "bigsky")
    raw(a, "vail", "landfire")                                     # SnowboardAnywhere\raw: a LANDFIRE folder only
    raw(b, "vail", "dem1m", "dem10m", "ept", "naip1m", "mapterhorn")   # Documents\snowboard-sim\raw: the full set
    vail = ci.check_inputs("", "", "vail", "", res)
    root, note = ci.pick_raw_root([a, b], vail, res)
    assert root == b and "5 raw layers" in note
    new = {"slug": "new-one", "deps": []}
    assert ci.pick_raw_root([a, b], new, res) == (a, "no raw data yet: it is fetched there")
    with pytest.raises(ci.Refused, match="SBA_RAW_ROOTS is empty"):
        ci.pick_raw_root([], new, res)


def test_a_resort_whose_source_is_in_another_root_is_refused(tmp_path):
    res, a, b = tmp_path / "resorts", str(tmp_path / "a"), str(tmp_path / "b")
    config(res, "boston-mills")
    config(res, "ohio-hills", raw_from="boston-mills", relocate=[{"source": "mad-river"}])
    config(res, "mad-river", source_only=True)
    raw(a, "boston-mills", "dem1m", "osm")
    raw(b, "mad-river", "dem1m")
    cfg = ci.check_inputs("", "", "ohio-hills", "", res)
    with pytest.raises(ci.Refused, match="mad-river's is in"):
        ci.pick_raw_root([a, b], cfg, res)
    raw(a, "mad-river", "dem1m")
    assert ci.pick_raw_root([a, b], cfg, res)[0] == a          # raw_from: boston-mills' folder decides


def test_pc_setup_points_the_steps_at_the_raw_root_the_game_and_one_index(tmp_path):
    res, a, b, game = tmp_path / "resorts", tmp_path / "a", tmp_path / "b", tmp_path / "sba-game"
    for d in (a, b):
        d.mkdir()
    config(res, "vail", lidar={"x": 1})
    raw(str(b), "vail", "dem1m", "ept")
    cfg = ci.check_inputs("", "", "vail", "", res)
    env = {"SBA_RAW_ROOTS": os.pathsep.join([str(a), str(b)]), "GAME_CHECKOUT": str(game)}
    with pytest.raises(ci.Refused, match="no game checkout"):
        ci.pc_setup(cfg, env, res)
    (game / "game").mkdir(parents=True)
    (game / "game" / "package.json").write_text("{}")
    got, _ = ci.pc_setup(cfg, env, res)
    assert got == {"SBA_RAW_ROOT": str(b), "SBA_GAME_REPO": str(game), "SBA_INDEX_DIR": os.path.join(str(a), "_index")}
    assert ci.pc_setup(cfg, {**env, "SBA_INDEX_DIR": "X"}, res)[0]["SBA_INDEX_DIR"] == "X"
    with pytest.raises(ci.Refused, match="is not a folder"):
        ci.pc_setup(cfg, {**env, "SBA_RAW_ROOTS": str(tmp_path / "gone")}, res)


# ------------------------------------------------------------------------------------------------ FEAT-342

def test_a_refresh_run_id_is_digits_and_reaches_publish_as_a_url(tmp_path, monkeypatch):
    config(tmp_path, "vail")
    for bad in ("0", "12a", "1; rm -rf /", "-5", "9" * 21):
        with pytest.raises(ci.Refused, match="not a workflow run id"):
            ci.check_inputs("", "", "vail", "refresh-packs", tmp_path, refresh_run=bad)
    got = ci.check_inputs("", "", "vail", "refresh-packs", tmp_path, refresh_run=" 77 ")
    assert got["refresh_run"] == "77"
    (cmd,) = ci.stage_commands("publish", {**got, "refresh_url": "https://github.com/o/r/actions/runs/77"})
    assert cmd[cmd.index("--refresh-run") + 1] == "https://github.com/o/r/actions/runs/77"
    (cmd,) = ci.stage_commands("publish", ci.check_inputs("", "", "vail", "", tmp_path))
    assert "--refresh-run" not in cmd

    seen = []
    monkeypatch.setattr(ci, "from_env", lambda: dict(got))
    monkeypatch.setenv("GITHUB_REPOSITORY", "o/r")
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.com")
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    assert ci.main(["publish"], runner=lambda c: seen.append(c) or (0, "")) == 0
    assert seen[0][seen[0].index("--refresh-run") + 1] == "https://github.com/o/r/actions/runs/77"


def test_the_env_carries_the_refresh_run(monkeypatch):
    monkeypatch.setenv("SLUG", "vail")
    monkeypatch.setenv("REFRESH_RUN", "123")
    for k in ("REBUILD", "NAME", "OSM_ID", "REQUESTED_BY"):
        monkeypatch.delenv(k, raising=False)
    assert ci.from_env()["refresh_run"] == "123"
