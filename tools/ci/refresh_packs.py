"""Refresh packs (FEAT-342, .github/workflows/refresh-packs.yml): rebuild every published pack that needs it with the
current pipeline, by starting one Build pack run per pack.

    python tools/ci/refresh_packs.py --mode "list only"        the plan, nothing started (also on Drew's PC)
    python tools/ci/refresh_packs.py --mode "needs updating"   start a build for each pack behind main
    python tools/ci/refresh_packs.py --mode all                start a build for every pack it can
    [--base origin/main] [--json plan.json] [--no-attract]
    python tools/ci/refresh_packs.py --start-pc [--json pc.json]   the workflow's `pc` job: start PC_SLUGS on Drew's PC

Pick: every resort in catalog.json (and its test packs, which are always left out: `publish_pack.py --synth`
builds and publishes the synthetic pack after a pipeline merge). In *needs updating* a pack is picked when its
catalog `pipeline` stamp is behind --base in a path its build reads (BUILD_PATHS: pipeline/ without its tests and
Markdown, the resort's own resorts/<slug>/ and manifests/<slug>.json, and those of the resorts it builds on, its
`raw_from` and relocate sources); a stamp git can't find (a pack built before the move to this repo, FEAT-238)
counts as behind. A wrong pick only costs runner time: publish_pack.py publishes nothing when the content is the
published version's.

To Drew's PC (action `pc`, reason `too_big`): a pack whose resorts/<slug>/runner.json says the free runner can't
build it ({"cloud": false, "reason": "too_big", "why": "..."}: Vail), picked by the same rules. The refresh job
does not start these: it hands their slugs to the workflow's `pc` job (the `pc` step output), which starts each
with build_on pc through --start-pc, as Drew (PC_DISPATCH_TOKEN), since the PC runner's locks take only a
maintainer's dispatch (docs/pc-runner.md > Refresh packs and the PC).

Left out, each with a reason code (the JSON plan's `reason`):
  test_pack          a catalog test pack (synth): publish_pack.py --synth, not Build pack
  no_config          no resorts/<slug>/<slug>.json, or a source_only one: Build pack can't rebuild it
  attract_unread     the published pack's attract/ could not be read (the release zip, by ranged reads of its
                     directory and that one file): left out rather than risk dropping a menu
  no_release         the catalog entry has no pack url

Started with a note: a pack published with a generated menu still or ghost takes (made by the game on a GPU,
FEAT-343). Its cloud build carries the published menu over (FEAT-345, `pipeline/release_zip.py carry_attract`): the
riders stay when the cameras do, and a pack that changed goes out without the still until a GPU renders one. The
row's `note` says so and `gpu_still` is true (FEAT-344 can route these to a GPU runner later).

Start: `gh api .../actions/workflows/build-pack.yml/dispatches` on main per picked pack, slug order, with
requested_by `refresh-packs` and refresh_run this run's id (publish_pack.py writes it in the publish PR, and
publish_merge.py lets the App's automerge label count when a maintainer started this run). *list only* starts
nothing and shows the needs updating plan. The run summary gets a table, one row per pack; --json writes the same rows as data. Exit 1 when a start
failed.
"""
import argparse, json, os, re, subprocess, sys
from typing import Callable

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import paths  # noqa: E402
from release_zip import RangeFile, published_attract  # noqa: E402,F401  (FEAT-345: shared with the build)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_pack_ci  # noqa: E402
import rebuild_choices  # noqa: E402

MODES = ("needs updating", "all", "list only")
WORKFLOW = "build-pack.yml"
REQUESTED_BY = "refresh-packs"
# what a build reads besides the resorts' own folders; pipeline/resorts and pipeline/manifests are where the configs
# lived before the move (build_resort.py NOT_BUILD)
BUILD_PATHS = ["pipeline", ":(exclude)pipeline/tests", ":(exclude,glob)pipeline/**/*.md",
               ":(exclude)pipeline/resorts", ":(exclude)pipeline/manifests"]
REASONS = {
    "test_pack": "a test pack: publish_pack.py --synth builds and publishes it",
    "no_config": "no config in resorts/ that Build pack can rebuild",
    "too_big": "too big for the free runner: built on Drew's PC",
    "attract_unread": "could not read the published menu (attract/): build on Drew's PC, or run again",
    "no_release": "no pack url in the catalog",
}
GPU_STILL_NOTE = "riders carried, still needs the PC: a changed pack goes out without its menu still"  # FEAT-345
# FEAT-385
PC_RUNNER = "sba-pc"                  # docs/pc-runner.md: the self-hosted runner's name and label
TOKEN = "PC_DISPATCH_TOKEN"           # the publish environment's secret the pc job starts PC builds with


def git(*args, cwd=ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def has_commit(sha: str, git=git) -> bool:
    return bool(sha) and re.fullmatch(r"[0-9a-f]{4,40}", sha) is not None and \
        git("cat-file", "-e", f"{sha}^{{commit}}").returncode == 0


def build_paths(slug: str, resorts=None) -> list[str]:
    """the git pathspecs a pack's build reads: BUILD_PATHS plus its resort folder and manifest and its sources'"""
    out = list(BUILD_PATHS)
    for s in build_pack_ci.deps(slug, resorts) + [slug]:
        out += [f"resorts/{s}", f"manifests/{s}.json"]
    return out


def behind(stamp: str, base: str, pathspecs: list[str], git=git) -> list[str] | None:
    """the files `base` changed since `stamp` in `pathspecs`, [] when none; None when git can't find the stamp"""
    if not has_commit(stamp, git):
        return None
    p = git("diff", "--name-only", stamp, base, "--", *pathspecs)
    if p.returncode:
        return None
    return [ln for ln in p.stdout.splitlines() if ln.strip()]


def runner(slug: str, resorts=None) -> dict:
    """resorts/<slug>/runner.json (FEAT-342): {"cloud": false, "reason": <code>, "why": <text>} for a pack the free
    runner can't build; {} when there is none"""
    path = paths.runner_path(slug, resorts)
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def needs_gpu(index: dict | None) -> bool:
    """a generated menu with stills or ghost takes: made by the game's tools on a GPU, which a cloud build skips"""
    return bool(index) and bool(index.get("generated")) and bool(index.get("stills") or index.get("ghosts"))


def plan(catalog: dict, mode: str, base: str, resorts=None, git=git, attract: Callable | None = published_attract,
         ) -> list[dict]:
    """one row per catalog pack: {slug, name, stamp, action: start | up_to_date | left_out, reason, detail}"""
    rows = []
    for e in catalog.get("test") or []:
        rows.append({"slug": e["slug"], "name": e.get("name", e["slug"]), "stamp": (e.get("pack") or {}).get("pipeline"),
                     "action": "left_out", "reason": "test_pack", "detail": REASONS["test_pack"]})
    for e in sorted(catalog.get("resorts") or [], key=lambda e: e["slug"]):
        slug, pack = e["slug"], e.get("pack") or {}
        row = {"slug": slug, "name": e.get("name", slug), "stamp": pack.get("pipeline"), "action": "start",
               "reason": None, "detail": ""}
        rows.append(row)

        def out(reason, detail=None):
            row.update(action="left_out", reason=reason, detail=detail or REASONS[reason])
        if not build_pack_ci.SLUG_RE.fullmatch(slug) or                 not rebuild_choices.rebuildable(slug, resorts or paths.RESORTS):
            out("no_config")
            continue
        pc = runner(slug, resorts).get("cloud") is False
        if mode != "all":         # list only shows the needs updating plan
            try:
                changed = behind(pack.get("pipeline") or "", base, build_paths(slug, resorts), git)
            except build_pack_ci.Refused as err:
                out("no_config", str(err))
                continue
            if changed == []:
                row.update(action="up_to_date", detail=f"nothing it builds from changed since {row['stamp']}")
                continue
            row["detail"] = (f"stamp {row['stamp']} is not in this repo's history" if changed is None else
                             f"{len(changed)} file(s) changed since {row['stamp']}: " + ", ".join(changed[:3])
                             + (", ..." if len(changed) > 3 else ""))
        else:
            row["detail"] = "mode all: every pack it can"
        if not pack.get("url"):
            out("no_release")
            continue
        if pc:                    # the PC renders the menu itself
            row.update(action="pc", reason="too_big", note=REASONS["too_big"])
            continue
        if attract:
            try:
                if needs_gpu(attract(pack["url"], int(pack.get("bytes") or 0))):
                    row.update(note=GPU_STILL_NOTE, gpu_still=True)
            except (OSError, ValueError) as err:
                out("attract_unread", f"{REASONS['attract_unread']}: {err}")
                continue
    return rows


def dispatch(repo: str, slug: str, refresh_run: str | None, build_on: str = "cloud") -> str:
    """start Build pack on main for `slug` -> the run's url (or the workflow's runs page when GitHub does not say)"""
    cmd = ["gh", "api", "-X", "POST", f"repos/{repo}/actions/workflows/{WORKFLOW}/dispatches", "-f", "ref=main",
           "-f", f"inputs[slug]={slug}", "-f", f"inputs[requested_by]={REQUESTED_BY}", "-F", "return_run_details=true"]
    if refresh_run:
        cmd += ["-f", f"inputs[refresh_run]={refresh_run}"]
    if build_on != "cloud":
        cmd += ["-f", f"inputs[build_on]={build_on}"]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout).strip())
    try:
        return json.loads(p.stdout).get("html_url") or ""
    except ValueError:
        return f"https://github.com/{repo}/actions/workflows/{WORKFLOW}"


def table(rows: list[dict], mode: str, base_sha: str) -> str:
    words = {"start": "would start" if mode == "list only" else "started", "up_to_date": "up to date",
             "pc": "would go to Drew's PC" if mode == "list only" else "to Drew's PC (the pc job's table)",
             "left_out": "left out", "start_failed": "**start failed**"}
    lines = [f"## Refresh packs ({mode})", "",
             f"Against `{base_sha}`. " + ", ".join(f"{sum(r['action'] == a for r in rows)} {w}"
                                                    for a, w in words.items() if any(r['action'] == a for r in rows))
             + ".", "", "| pack | stamp | result | why |", "|---|---|---|---|"]
    for r in rows:
        res = words[r["action"]] + (f" ([run]({r['run_url']}))" if r.get("run_url") else "")
        why = (f"`{r['reason']}`: " if r.get("reason") else "") + build_pack_ci.md(r.get("detail") or "") +             (f" **Note:** {build_pack_ci.md(r['note'])}" if r.get("note") and r["action"] != "left_out" else "")
        lines.append(f"| {build_pack_ci.md(r['name'])} (`{r['slug']}`) | `{r.get('stamp') or '-'}` | {res} | {why} |")
    return "\n".join(lines) + "\n"


def runner_status(repo: str) -> str | None:
    """sba-pc's status ("online", "offline"; "offline" when it is not registered), or None when the token can't list
    the repo's runners (that needs Administration: read; a token with Actions only gets 403)"""
    p = subprocess.run(["gh", "api", f"repos/{repo}/actions/runners", "--jq",
                        f'.runners[] | select(.name == "{PC_RUNNER}") | .status'], capture_output=True, text=True)
    return None if p.returncode else (p.stdout.strip() or "offline")


def start_pc(slugs: list, repo: str, own: str | None, token: str, start: Callable = dispatch,
             status: Callable = runner_status, resorts=None) -> tuple[list[dict], list[str]]:
    """the pc job: start Build pack with build_on pc for each slug the refresh job handed over (only a slug whose
    runner.json says cloud false), as the token's owner -> (rows, lines for above the table)"""
    ok = [s for s in slugs if isinstance(s, str) and build_pack_ci.SLUG_RE.fullmatch(s)
          and runner(s, resorts).get("cloud") is False]
    rows = [{"slug": str(s), "action": "refused", "detail": "not a pack its runner.json sends to the PC"}
            for s in slugs if s not in ok]
    if not token:
        return rows + [{"slug": s, "action": "not_started", "detail": f"{TOKEN} is not set"} for s in ok], [
            f"**{TOKEN} is not set** in the `publish` environment, so nothing was started on Drew's PC "
            "(docs/pc-runner.md > The dispatch token)."]
    st = status(repo)
    lines = [f"Runner `{PC_RUNNER}`: " + (
        "online." if st == "online" else
        "**offline**: the builds wait in GitHub's queue (24 hours at most) until it is back." if st else
        f"status not readable ({TOKEN} has no Administration: read); a build waits in GitHub's queue while the PC "
        "is offline.")]
    for s in ok:
        row = {"slug": s, "action": "queued_offline" if st == "offline" else "building", "detail": ""}
        try:
            row["run_url"] = start(repo, s, own, "pc")
            print(f"started {s} on Drew's PC: {row['run_url']}", flush=True)
        except Exception as err:   # one failed start must not stop the rest
            refused = any(k in str(err) for k in ("HTTP 401", "HTTP 403", "Bad credentials"))
            row.update(action="not_started", detail=f"GitHub refused {TOKEN} (expired, revoked, or without Actions: "
                       f"read and write on this repo): {err}" if refused else str(err))
            print(f"::error::could not start {s} on Drew's PC: {row['detail']}", flush=True)
        rows.append(row)
    return rows, lines


def pc_table(rows: list[dict], lines: list[str]) -> str:
    words = {"building": "building on Drew's PC", "queued_offline": "queued: PC runner offline",
             "not_started": "**not started**", "refused": "**refused**"}
    out = ["## Refresh packs: Drew's PC", "", *lines, "", "| pack | result | why |", "|---|---|---|"]
    for r in rows:
        res = words[r["action"]] + (f" ([run]({r['run_url']}))" if r.get("run_url") else "")
        why = build_pack_ci.md(r.get("detail") or "") + (
            f"; still needs a hand build: `gh workflow run {WORKFLOW} -f slug={r['slug']} -f build_on=pc`" if r["action"] == "not_started" else "")
        out.append(f"| `{r['slug']}` | {res} | {why} |")
    return "\n".join(out) + "\n"


def report(text: str, path: str | None, doc: dict) -> None:
    """print the summary, add it to the run summary, write the JSON"""
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(text)
    if path:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(doc, f, indent=1)
            f.write("\n")


def main(argv=None, start: Callable = dispatch, status: Callable = runner_status) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--mode", choices=MODES, default=os.environ.get("MODE") or "needs updating")
    ap.add_argument("--base", default=None, help="the commit packs are compared with (default origin/main, else HEAD)")
    ap.add_argument("--catalog", default=os.path.join(ROOT, "catalog.json"))
    ap.add_argument("--json", help="write the plan here as JSON (rows with a reason code each)")
    ap.add_argument("--no-attract", action="store_true", help="don't read the published packs' attract/")
    ap.add_argument("--start-pc", action="store_true",
                    help="start the PC_SLUGS packs (a JSON list) on Drew's PC with GH_TOKEN (the pc job)")
    a = ap.parse_args(argv)
    repo, own = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_RUN_ID")
    if not repo and (a.start_pc or a.mode != "list only"):
        print("GITHUB_REPOSITORY must be set to start builds (this runs inside a workflow); use --mode 'list only'")
        return 2
    if a.start_pc:
        try:
            slugs = json.loads(os.environ.get("PC_SLUGS") or "[]")
        except ValueError:
            slugs = None
        if not isinstance(slugs, list):
            print(f"PC_SLUGS is not a JSON list: {os.environ.get('PC_SLUGS')!r}")
            return 2
        rows, lines = start_pc(slugs, repo, own, os.environ.get("GH_TOKEN") or "", start, status)
        report(pc_table(rows, lines), a.json, {"packs": rows})
        return 1 if any(r["action"] in ("not_started", "refused") for r in rows) else 0
    base = a.base or ("origin/main" if git("rev-parse", "--verify", "-q", "origin/main").returncode == 0 else "HEAD")
    base_sha = git("rev-parse", "--short", base).stdout.strip() or base
    with open(a.catalog, encoding="utf-8") as f:
        catalog = json.load(f)
    rows = plan(catalog, a.mode, base, attract=None if a.no_attract else published_attract)
    if a.mode != "list only":
        if os.environ.get("GITHUB_OUTPUT"):     # the pc job's packs, written first so a failed cloud start keeps them
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
                f.write(f"pc={json.dumps([r['slug'] for r in rows if r['action'] == 'pc'])}\n")
        for r in rows:
            if r["action"] != "start":
                continue
            try:
                r["run_url"] = start(repo, r["slug"], own)
                print(f"started {r['slug']}: {r['run_url']}", flush=True)
            except Exception as err:   # one failed start must not stop the rest
                r.update(action="start_failed", detail=str(err))
                print(f"::error::could not start {r['slug']}: {err}", flush=True)
    report(table(rows, a.mode, base_sha), a.json, {"mode": a.mode, "base": base_sha, "packs": rows,
                                                   "left_out": [r for r in rows if r["action"] == "left_out"]})
    return 1 if any(r["action"] == "start_failed" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
