"""tools/ci/build_failures.py (FEAT-314): failure reasons, the retry decision and the metrics, without the network.
The four logs are trimmed from the failed runs of 2026-11-13 and 14 the card lists."""
import json, os, subprocess, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools", "ci"))
import build_failures as bf  # noqa: E402

T = "2026-11-14T09:06:41.0723192Z "
PROBE_GEOFABRIK = "\n".join(T + l for l in [
    "ok   LANDFIRE LFPS: HTTP 500, LFPS JSON",
    "FAIL Geofabrik index: curl: (7) Failed to connect to download.geofabrik.de port 443 after 811 ms: Could not connect to server",
    "LANDFIRE LFPS                    ok                    0.2 s  HTTP 500, LFPS JSON",
    "Geofabrik index                  FAIL                 21.6 s  curl: (7) Failed to connect to download.geofabrik.de port 443",
    "unreachable: download.geofabrik.de",
    "##[error]Process completed with exit code 1.",
    "Post job cleanup.",
    "Removing HTTP extra header"])
PROBE_WESM = "\n".join(T + l for l in [
    "ok   LANDFIRE LFPS: HTTP 500, LFPS JSON",
    'FAIL 3DEP elevation index (WESM): JSON without features: {"error":{"code":400,"message":"Failed to execute query.","details":[]}}',
    "unreachable: index.nationalmap.gov",
    "##[error]Process completed with exit code 1."])
QUEUE_502 = "\n".join(T + l for l in [
    "Traceback (most recent call last):",
    '    raise RuntimeError(f"gh api failed: {p.stderr.strip()}")',
    "RuntimeError: gh api failed: gh: Server Error (HTTP 502)",
    "##[error]Process completed with exit code 1."])
ASPEN = "\n".join(T + l for l in [
    "08:16:51    retry osm/ski.json (4) after error: HTTP 502 -> overpass.private.coffee",
    "08:22:54  Finished: 1694 downloaded (1,531 MB), 0 skipped, 0 failed",
    "stopped: raw data incomplete in /home/runner/sba-raw/aspen-hills: OSM pistes_wide (no elements). Delete any bad "
    "files and run again with --force fetch (it downloads only what is missing)",
    "| fetch | **failed** (exit 1) | 724 s |",
    "##[error]Process completed with exit code 1."])


def test_the_four_failures_of_the_card_are_classified():
    assert bf.classify("data hosts", PROBE_GEOFABRIK) == {"reason": "connect", "transient": True,
                                                         "host": "download.geofabrik.de"}
    assert bf.classify("data hosts", PROBE_WESM) == {"reason": "arcgis-400", "transient": True,
                                                    "host": "index.nationalmap.gov"}
    assert bf.classify("wait for the builds started before this one", QUEUE_502) == {
        "reason": "github-api", "transient": True, "host": "api.github.com"}
    # the earlier 502 retries passed; the stop is the raw check, a real cause
    assert bf.classify("fetch", ASPEN) == {"reason": "raw-incomplete", "transient": False, "host": ""}


def test_real_causes_and_cancelled_are_not_retried():
    assert not bf.classify("build", "No space left on device\n##[error]x")["transient"]
    assert bf.classify("build", "Traceback (most recent call last):\nKeyError: 'x'\n##[error]x")["reason"] == "code-error"
    assert bf.classify("x", "something odd\n##[error]x") == {"reason": "unknown", "transient": False, "host": ""}
    assert bf.classify("fetch", "", "cancelled")["reason"] == "cancelled"
    # an Overpass error page caught by the raw check is busy, not missing data
    log = "stopped: raw data incomplete: OSM ski (no elements: runtime error: Query timed out)\n##[error]x"
    assert bf.classify("fetch", log)["reason"] == "overpass-busy"


def test_an_old_retry_line_never_makes_an_unknown_stop_transient():
    """review on #132: a fetch full of 502 retries that passed, then a stop no rule knows"""
    retries = [f"retry osm/ski.json ({k}) after error: HTTP 502 -> overpass.private.coffee" for k in range(5)]
    log = "\n".join(retries + [f"... {k} done" for k in range(40)] + ["exit status 3", "##[error]Process completed"])
    assert bf.classify("fetch", log) == {"reason": "unknown", "transient": False, "host": ""}
    # and only the failed step counts: a 502 in an earlier step's output is not this step's cause
    log = "\n".join(["##[group]Run earlier", "HTTP 502", "##[group]Run python tools/ci/build_pack_ci.py fetch",
                     "boom", "##[error]Process completed"])
    assert bf.classify("fetch", log)["reason"] == "unknown"


def job(name, conclusion, step=None, start="2026-11-14T09:00:00Z", end="2026-11-14T09:10:00Z", id=1):
    steps = [{"name": "setup", "conclusion": "success"}] + ([{"name": step, "conclusion": conclusion}] if step else [])
    return {"id": id, "name": name, "conclusion": conclusion, "started_at": start, "completed_at": end, "steps": steps}


def run_record(monkeypatch, tmp_path, jobs, attempt, logs=None):
    monkeypatch.setenv("GITHUB_REPOSITORY", "o/r")
    monkeypatch.setenv("GITHUB_RUN_ID", "42")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", str(attempt))
    monkeypatch.setenv("SLUG", "vail")
    for k in ("REBUILD", "NAME", "OSM_ID", "REQUESTED_BY"):
        monkeypatch.delenv(k, raising=False)
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    saved, sent = [], []

    def save(row):
        saved.append(row)
        return saved, bf.tuning(saved)
    assert bf.record(save=save, jobs=jobs, log_of=lambda j: (logs or {}).get(j["name"], ""),
                     dispatch=lambda: sent.append(attempt)) == 0
    return saved[-1], sent, summary.read_text(encoding="utf-8")


def test_a_transient_failure_retries_twice_then_gives_up(monkeypatch, tmp_path):
    jobs = [job("queue", "success"), job("probe", "failure", "data hosts", id=7), job("build", "skipped"),
            job("outcome", None)]
    row, sent, text = run_record(monkeypatch, tmp_path, jobs, 1, {"probe": PROBE_GEOFABRIK})
    assert row["outcome"] == "retrying" and sent == [1] and row["pack"] == "vail"
    assert (row["job"], row["step"], row["host"], row["duration_s"]) == ("probe", "data hosts", "download.geofabrik.de", 600)
    assert "re-running the failed jobs in 5 min (attempt 2 of 3)" in text
    row, sent, _ = run_record(monkeypatch, tmp_path, jobs, 3, {"probe": PROBE_GEOFABRIK})
    assert row["outcome"] == "gave up" and sent == []


def test_a_real_failure_stops_on_the_first_try(monkeypatch, tmp_path, capsys):
    jobs = [job("queue", "success"), job("probe", "success"), job("build", "failure", "fetch"), job("outcome", None)]
    row, sent, text = run_record(monkeypatch, tmp_path, jobs, 1, {"build": ASPEN})
    assert row["outcome"] == "stopped" and sent == [] and "a real failure, not retried" in text
    assert "::error::Build pack stopped: raw-incomplete at build / fetch" in capsys.readouterr().out


def test_a_passed_attempt_is_logged_too(monkeypatch, tmp_path):
    row, sent, text = run_record(monkeypatch, tmp_path, [job("build", "success"), job("outcome", None)], 2)
    assert row["outcome"] == "passed" and row["reason"] == "" and sent == [] and "passed on attempt 2" in text


def test_the_summary_counts_hosts_reasons_and_retry_success():
    rows = [{"run_id": 1, "attempt": 1, "job": "probe", "step": "data hosts", "host": "a.org", "reason": "timeout",
             "transient": True, "outcome": "retrying"},
            {"run_id": 1, "attempt": 2, "job": "build", "step": "fetch", "host": "", "reason": "", "transient": False,
             "outcome": "passed"},
            {"run_id": 2, "attempt": 1, "job": "probe", "step": "data hosts", "host": "a.org", "reason": "timeout",
             "transient": True, "outcome": "retrying"},
            {"run_id": 2, "attempt": 2, "job": "probe", "step": "data hosts", "host": "a.org", "reason": "connect",
             "transient": True, "outcome": "retrying"}]
    assert bf.retry_stats(rows) == (2, 1)
    tune = bf.tuning(rows)
    assert tune == {"a.org": {"timeout": 135, "tries": 4}}           # 3 timeouts: 60 s * 1.5 ** 2, one more try
    text = bf.summary_md(rows, tune)
    assert "| a.org | 3 |" in text and "timeout (transient)" in text and "50%" in text and "| a.org | 135 s | 4 |" in text


def test_tuning_grows_with_the_failures_and_stops_at_the_cap():
    def rows(n):
        return [{"host": "h", "reason": "timeout", "job": "probe"} for _ in range(n)]
    assert bf.tuning(rows(1)) == {}
    assert bf.tuning(rows(2)) == {"h": {"timeout": 90, "tries": 4}}
    assert bf.tuning(rows(10)) == {"h": {"timeout": bf.CAP["timeout"], "tries": bf.CAP["tries"]}}
    assert bf.tuning([{"host": "h", "reason": "timeout", "job": "build"}] * 5) == {}    # the fetch has its own retries


def test_retry_waits_for_the_run_then_reruns_once(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "o/r")
    states = iter([{"path": ".github/workflows/build-pack.yml"}, {"status": "in_progress"},
                   {"status": "completed", "conclusion": "failure", "run_attempt": 1},
                   {"status": "completed", "conclusion": "failure", "run_attempt": 1}])
    slept, ran = [], []
    assert bf.retry("42", 1, sleep=slept.append, view=lambda: next(states), rerun=lambda: ran.append(1)) == 0
    assert slept == [30, 300] and ran == [1]
    # someone re-ran it by hand while it waited: nothing
    states = iter([{"path": ".github/workflows/build-pack.yml"}, {"status": "completed", "conclusion": "failure", "run_attempt": 2},
                   {"status": "completed", "conclusion": "failure", "run_attempt": 3}])
    ran = []
    assert bf.retry("42", 2, sleep=lambda s: None, view=lambda: next(states), rerun=lambda: ran.append(1)) == 0
    assert ran == []
    # never a run of another workflow
    assert bf.retry("42", 1, sleep=lambda s: None, view=lambda: {"path": ".github/workflows/checks.yml"},
                    rerun=lambda: ran.append(1)) == 2 and ran == []


def test_the_retry_command_refuses_bad_inputs(monkeypatch):
    monkeypatch.setenv("RETRY_RUN_ID", "42; rm -rf /")
    monkeypatch.setenv("RETRY_ATTEMPT", "1")
    assert bf.main(["retry"]) == 2
    monkeypatch.setenv("RETRY_RUN_ID", "42")
    monkeypatch.setenv("RETRY_ATTEMPT", "3")
    assert bf.main(["retry"]) == 2


def test_save_row_appends_to_the_metrics_branch(tmp_path):
    """against a local bare 'origin': the first row makes the branch, the second appends"""
    def sh(*a, cwd):
        subprocess.run(a, cwd=cwd, check=True, capture_output=True)
    origin, work = tmp_path / "origin.git", tmp_path / "work"
    sh("git", "init", "-q", "--bare", str(origin), cwd=tmp_path)
    sh("git", "init", "-q", "-b", "main", str(work), cwd=tmp_path)
    (work / "f").write_text("x")
    sh("git", "add", "f", cwd=work)
    sh("git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x", cwd=work)
    sh("git", "remote", "add", "origin", str(origin), cwd=work)
    row = {"run_id": 1, "pack": "vail", "attempt": 1, "job": "probe", "step": "data hosts", "host": "h",
           "reason": "timeout", "transient": True, "duration_s": 5, "outcome": "retrying"}
    bf.save_row(row, str(work))
    rows, tune = bf.save_row(dict(row, attempt=2), str(work))
    assert [r["attempt"] for r in rows] == [1, 2] and tune == {"h": {"timeout": 90, "tries": 4}}
    out = subprocess.run(["git", "--git-dir", str(origin), "show", "metrics:build-failures.jsonl"],
                         capture_output=True, text=True).stdout
    assert len(out.splitlines()) == 2 and json.loads(out.splitlines()[1])["attempt"] == 2
    files = subprocess.run(["git", "--git-dir", str(origin), "ls-tree", "--name-only", "metrics"],
                           capture_output=True, text=True).stdout.split()
    assert sorted(files) == ["README.md", "build-failures.jsonl", "host-tuning.json"]     # nothing from main


def test_a_4xx_is_real_at_every_layer():
    """FEAT-314 refinement: the probe and the fetch say a 4xx was not retried, and the job is not re-run either"""
    probe = "\n".join(T + l for l in ["FAIL Geofabrik index: HTTP 404 (a 4xx: not retried)",
                                       "unreachable: download.geofabrik.de", "##[error]Process completed with exit code 1."])
    assert bf.classify("data hosts", probe) == {"reason": "http-4xx", "transient": False, "host": "download.geofabrik.de"}
    fetch = "\n".join(T + l for l in [
        "08:16:51    FAILED naip1m/x.tif: HTTP 403 (a 4xx: not retried)",
        "stopped: a download was refused (a 4xx: not retried; /raw/x/fetch_log.txt lists it): fix the manifest",
        "| fetch | **failed** (exit 1) | 724 s |", "##[error]Process completed with exit code 1."])
    assert bf.classify("fetch", fetch)["reason"] == "http-4xx" and not bf.classify("fetch", fetch)["transient"]
    assert bf.classify("x", T + "HTTP 429\n##[error]x")["reason"] == "rate-limit"       # 429 stays transient


def test_inline_retries_are_counted_per_host_and_summarised(tmp_path):
    (tmp_path / "inline-retries-probe-1").mkdir()
    (tmp_path / "inline-retries-probe-1" / "inline-retries.jsonl").write_text(
        json.dumps({"tool": "probe", "host": "a.org", "calls": 1, "retried": 1, "recovered": 1, "failed": 0}) + "\n")
    (tmp_path / "b.jsonl").write_text(
        json.dumps({"tool": "fetch", "host": "a.org", "calls": 40, "retried": 3, "recovered": 2, "failed": 1}) + "\nnot json\n")
    inline = bf.inline_counts(str(tmp_path))
    assert inline == {"a.org": {"calls": 41, "retried": 4, "recovered": 3, "failed": 1}}
    assert bf.inline_counts(None) == {}
    rows = [{"run_id": 1, "attempt": 1, "job": "build", "step": "fetch", "host": "", "reason": "", "transient": False,
             "outcome": "passed", "inline": inline},
            {"run_id": 2, "attempt": 1, "job": "probe", "step": "data hosts", "host": "b.org", "reason": "http-4xx",
             "transient": False, "outcome": "stopped"}]
    text = bf.summary_md(rows, {})
    assert "Recovered inline: 3 calls; job re-runs: 0; real failures: 1" in text
    assert "| a.org | 41 | 4 | 3 | 1 |" in text


# ---------------------------------------------------------------- BUG-171


class Answer:
    def __init__(self, code, out="", err=""):
        self.returncode, self.stdout, self.stderr = code, out, err


def test_job_log_waits_for_a_log_that_lags_the_job(capsys):
    """the outcome job starts seconds after the job it reads; the log can come later"""
    answers = iter([Answer(1, err="HTTP 404: Not Found"), Answer(0, ""), Answer(0, "##[error]the log")])
    waits = []
    assert bf.job_log("o/r", 7, sleep=waits.append, api=lambda: next(answers)) == "##[error]the log"
    assert waits == [0, 10, 20] and "::warning::" not in capsys.readouterr().out


def test_job_log_gives_up_with_the_error_as_a_warning(capsys):
    waits = []
    assert bf.job_log("o/r", 7, sleep=waits.append, api=lambda: Answer(1, err="HTTP 403: Resource not accessible")) == ""
    assert waits == [0, *bf.LOG_WAITS]
    assert "::warning::the log of job 7 could not be read: HTTP 403: Resource not accessible" in capsys.readouterr().out


def test_a_failure_whose_log_cannot_be_read_is_retried_not_stopped(monkeypatch, tmp_path):
    """BUG-171: every failure read as `unknown` (a real stop) when the log came back empty, so no retry ever ran"""
    jobs = [job("queue", "success"), job("probe", "success"), job("build", "failure", "fetch", id=9),
            job("outcome", None)]
    row, sent, text = run_record(monkeypatch, tmp_path, jobs, 1, {})
    assert (row["reason"], row["transient"], row["outcome"]) == ("log-unreadable", True, "retrying") and sent == [1]
    assert "**log-unreadable** (transient) at build / fetch" in text


# ---------------------------------------------------------------- FEAT-388


HOOK_REFUSED = "\n".join(T + l for l in [
    "##[group]Run C:/sba-runner-hook/job_started.ps1",
    "##[error]This runner (Drew's PC) takes only Build pack from main, dispatched by a maintainer. Refused:",
    "  - actor 'someone' is not a maintainer",
    "##[error]Process completed with exit code 1."])


def test_a_pc_build_gets_one_free_retry_for_a_real_cause(monkeypatch, tmp_path):
    monkeypatch.setenv("BUILD_ON", "pc")
    jobs = [job("queue", "success"), job("probe", "success"), job("build", "failure", "build"), job("outcome", None)]
    log = {"build": "Traceback (most recent call last):\nKeyError: 'x'\n##[error]x"}
    row, sent, text = run_record(monkeypatch, tmp_path, jobs, 1, log)
    assert (row["reason"], row["transient"], row["outcome"]) == ("code-error", False, "pc retry") and sent == [1]
    assert "a build on Drew's PC gets one re-run whatever the cause" in text
    # the free retry is spent: the same cause on attempt 2 stops, and so does a run already re-run for a transient one
    row, sent, _ = run_record(monkeypatch, tmp_path, jobs, 2, log)
    assert row["outcome"] == "stopped" and sent == []
    # a transient cause keeps its two retries on the PC too
    row, sent, _ = run_record(monkeypatch, tmp_path, jobs, 2, {"build": QUEUE_502})
    assert row["outcome"] == "retrying" and sent == [2]
    # and the cloud has no free retry
    monkeypatch.setenv("BUILD_ON", "cloud")
    row, sent, _ = run_record(monkeypatch, tmp_path, jobs, 1, log)
    assert row["outcome"] == "stopped" and sent == []


def test_a_pc_build_is_not_re_run_for_a_cause_a_re_run_cannot_change(monkeypatch, tmp_path):
    monkeypatch.setenv("BUILD_ON", "pc")
    setup = "\n".join(["##[group]Run python tools/ci/build_pack_ci.py pc-setup",
                       "**Refused:** no game checkout at C:/x (GAME_CHECKOUT): the attract and spots stages need it",
                       "##[error]Process completed with exit code 1."])
    for conclusion, log, reason in (("failure", setup, "bad-input"),
                                    ("failure", "No space left on device\n##[error]x", "out-of-disk"),
                                    ("failure", HOOK_REFUSED, "pc-refused"),
                                    ("cancelled", "", "cancelled"),
                                    ("timed_out", "x\n##[error]x", "job-timeout")):
        jobs = [job("queue", "success"), job("probe", "success"), job("build", conclusion, "pc setup"),
                job("outcome", None)]
        row, sent, _ = run_record(monkeypatch, tmp_path, jobs, 1, {"build": log})
        assert (row["reason"], row["outcome"], sent) == (reason, "stopped", []), reason
    assert bf.classify("x", HOOK_REFUSED)["reason"] == "pc-refused"


def test_the_summary_counts_the_pc_retry_as_a_re_run_and_a_real_failure():
    rows = [{"run_id": 1, "attempt": 1, "job": "build", "step": "build", "host": "", "reason": "unknown",
             "transient": False, "outcome": "pc retry"},
            {"run_id": 1, "attempt": 2, "job": "build", "step": "build", "host": "", "reason": "", "transient": False,
             "outcome": "passed"}]
    assert bf.retry_stats(rows) == (1, 1)
    text = bf.summary_md(rows, {})
    assert "job re-runs: 1 (the PC's free retry: 1); real failures: 1" in text and "| unknown (real) | 1 |" in text
