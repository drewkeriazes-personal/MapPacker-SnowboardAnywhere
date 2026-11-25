"""Wait for this run's turn among the build-pack runs (FEAT-245): N builds at a time (FEAT-342), the rest queue in order.

    python tools/ci/wait_turn.py [--workflow build-pack.yml] [--slots N] [--poll 60] [--max-wait 330]

GitHub's `concurrency` keeps only one pending run per group and cancels an older pending one when a newer one
arrives, so it cannot hold a queue of more than one. Instead every run starts at once and this waits while any
run of the same workflow that started earlier (its current attempt's `run_started_at`, then the id) has not
completed; with --slots N (FEAT-342, Refresh packs) it waits while N or more of them have not, so N build at once.
--slots defaults to the BUILD_SLOTS environment variable (build-pack.yml passes the repo variable), else 1: one
at a time, as before. The oldest run never waits, so the queue always moves. The workflow runs it again at the start of the
build job, so "Re-run failed jobs", which skips a queue job that passed, still waits its turn. Reads the runs with `gh api` (GH_TOKEN; actions: read), for GITHUB_REPOSITORY and
GITHUB_RUN_ID. Gives up after --max-wait minutes with exit 1 (a job may run 6 hours at most).

Drew's PC (build_on pc, BUILD_ON in the environment) has no slot: the runner `sba-pc` is one machine and GitHub
gives it one job at a time, holding the rest in its own queue (24 hours) while it is busy or offline, so a PC run
never waits here, and a cloud run does not count the runs ahead of it whose build job is on the PC (its labels name
sba-pc; a run whose build job does not exist yet, or whose jobs can't be read, counts). So a PC build waiting for
an offline PC holds no cloud build back.
"""
import argparse, json, os, subprocess, sys, time
from typing import Callable

ACTIVE = ("queued", "in_progress", "waiting", "requested", "pending")
PC_LABEL = "sba-pc"


def order(r: dict, own: dict | None = None) -> tuple:
    """a run's place in the queue: when its current attempt started (`run_started_at`, which a re-run resets, so
    a re-run of an old run queues behind the builds in flight), then its id; the id alone when either run has no
    start time"""
    if own is not None and not (r.get("run_started_at") and own.get("run_started_at")):
        return ("", int(r["id"]))
    return (r.get("run_started_at") or "", int(r["id"]))


def slots_from(value) -> int:
    """the slot count from --slots or BUILD_SLOTS: a whole number of at least 1; empty or anything else is 1 (an unset
    repo variable reaches the step as an empty string)"""
    try:
        return max(1, int(str(value).strip()))
    except (TypeError, ValueError):
        return 1


def blocking(runs: list, own_id: int) -> list:
    """the runs ahead of `own_id`: not completed and started before it, oldest first"""
    own = next((r for r in runs if int(r["id"]) == own_id), {"id": own_id})
    key = lambda r: order(r, own)   # noqa: E731
    ahead = [r for r in runs if int(r["id"]) != own_id and r.get("status") in ACTIVE and key(r) < key(own)]
    return sorted(ahead, key=key)


def gh_runs(repo: str, workflow: str) -> list:
    """this workflow's runs in every not-completed status"""
    out = []
    for st in ACTIVE:
        for k in range(3):     # FEAT-314: GitHub's API answers 502 at times (bigsky, run 43573684184)
            p = subprocess.run(["gh", "api", "--paginate",
                                f"repos/{repo}/actions/workflows/{workflow}/runs?status={st}&per_page=100",
                                "--jq", ".workflow_runs[] | {id, status, run_number, html_url, run_started_at}"],
                               capture_output=True, text=True)
            if not p.returncode or k == 2:
                break
            print(f"gh api failed, trying again in 15 s: {p.stderr.strip()}", flush=True)
            time.sleep(15)
        if p.returncode:
            raise RuntimeError(f"gh api failed: {p.stderr.strip()}")
        out += [json.loads(line) for line in p.stdout.splitlines() if line.strip()]
    return out


def gh_on_pc(repo: str, run_id) -> bool:
    """the run's build job is on Drew's PC (its labels); False when its jobs can't be read"""
    p = subprocess.run(["gh", "api", f"repos/{repo}/actions/runs/{run_id}/jobs", "--jq", ".jobs[].labels[]"],
                       capture_output=True, text=True)
    return not p.returncode and PC_LABEL in p.stdout.split()


def describe(r: dict) -> str:
    return f"#{r.get('run_number', '?')} ({r['status']}) {r.get('html_url', r['id'])}"


def main(argv=None, list_runs: Callable | None = None, sleep: Callable = time.sleep,
         clock: Callable = time.monotonic, on_pc: Callable | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--workflow", default="build-pack.yml", help="workflow file name (default build-pack.yml)")
    ap.add_argument("--slots", default=None,
                    help="builds that may run at once (default: the BUILD_SLOTS environment variable, else 1)")
    ap.add_argument("--poll", type=int, default=60, help="seconds between looks (default 60)")
    ap.add_argument("--max-wait", type=float, default=330, help="minutes to wait before giving up (default 330)")
    a = ap.parse_args(argv)
    repo = os.environ.get("GITHUB_REPOSITORY")
    own = os.environ.get("GITHUB_RUN_ID")
    if not repo or not own:
        print("GITHUB_REPOSITORY and GITHUB_RUN_ID must be set (this runs inside a workflow)")
        return 2
    own_id = int(own)
    # FEAT-385
    if (os.environ.get("BUILD_ON") or "").strip() == "pc":
        print("Drew's PC: no cloud slot; its runner takes one build at a time", flush=True)
        return 0
    slots = slots_from(a.slots if a.slots is not None else os.environ.get("BUILD_SLOTS"))
    if slots > 1:
        print(f"{slots} builds at a time", flush=True)
    list_runs = list_runs or (lambda: gh_runs(repo, a.workflow))
    on_pc = on_pc or (lambda i: gh_on_pc(repo, i))
    pc = set()            # a run whose build job is on the PC stays there
    t0 = clock()
    last = None
    while True:
        ahead = blocking(list_runs(), own_id)
        pc |= {r["id"] for r in ahead if r["id"] not in pc and on_pc(r["id"])}
        ahead = [r for r in ahead if r["id"] not in pc]
        if len(ahead) < slots:
            waited = clock() - t0
            print("my turn" + (f" after {waited / 60:.0f} min" if waited >= 60 else ""), flush=True)
            return 0
        ids = [r["id"] for r in ahead]
        if ids != last:
            at_once = f", {slots} at a time" if slots > 1 else ""
            print(f"waiting for {len(ahead)} earlier build(s){at_once}: " + ", ".join(describe(r) for r in ahead),
                  flush=True)
            last = ids
        if clock() - t0 > a.max_wait * 60:
            print(f"gave up after {a.max_wait:.0f} min with {len(ahead)} build(s) still ahead; run it again later")
            return 1
        sleep(a.poll)


if __name__ == "__main__":
    sys.exit(main())
