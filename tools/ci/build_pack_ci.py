"""The steps of the build-pack workflow (FEAT-245, .github/workflows/build-pack.yml): one resort in, one publish PR out.

    python tools/ci/build_pack_ci.py check      check the run's inputs (the probe job, before anything runs)
    python tools/ci/build_pack_ci.py where      FEAT-344: cloud or Drew's PC (BUILD_ON); refuses a PC run that is not
                                                a workflow_dispatch on main by a maintainer (the probe job's output)
    python tools/ci/build_pack_ci.py pc-setup   FEAT-344, on Drew's PC only: the raw root that already holds the
                                                resort's data (SBA_RAW_ROOTS) and the game checkout (GAME_CHECKOUT)
                                                for the attract and spots stages, into $GITHUB_ENV
    python tools/ci/build_pack_ci.py inputs     the same, then write the step outputs and the summary's heading
    python tools/ci/build_pack_ci.py resolve    new slug: resort.py add --osm ... --stop-after plan; rebuild: skip
    python tools/ci/build_pack_ci.py fetch      build_resort.py data stages, for the raw data it builds on first
    python tools/ci/build_pack_ci.py build      build_resort.py build to index (attract and spots skip on the free
                                                runner, which has no game, and the published menu riders are
                                                carried over instead, FEAT-345 below; on Drew's PC they run, on the GPU)
    python tools/ci/build_pack_ci.py report     build_resort.py report (the DATA-022 scorecard, not a gate here)
    python tools/ci/build_pack_ci.py publish    publish_pack.py: a draft release and a publish PR, or nothing when
                                                the pack is the same as the one published (or already in a PR)

The inputs are untrusted text (anyone with write access can start a run, and later the game's Build it button
passes a typed name). The workflow hands them over as environment variables, never in a shell line, and `inputs`
refuses anything outside the shapes below before any other step runs. Every step appends a line to the run
summary ($GITHUB_STEP_SUMMARY); the steps are named after the stages, so the game can read progress from the
run's jobs (FEAT-247).

The menu (FEAT-345), on the free runner only (BUILD_ON cloud; on Drew's PC the attract stage renders it): the
runner has no game, so it can't render a menu still or ride ghost takes, and it starts with an empty packs/<slug>/. Before the build, `build` copies the published pack's generated attract/ (the still, the
takes, the shots) into packs/<slug>/attract/ by ranged reads of the release zip (`release_zip.carry_attract`), and
`gen_content.py write_attract` keeps it when the new shots are the same (checking each take against the new heights)
or drops it when they are not, as on Drew's PC. No published pack, or the read fails: nothing is carried, the run
summary says why, and the build goes on. After the build, a still the game would not show (rendered from another
build) stays only when the pack came out the same as the published one (the same `content` key: nothing will
publish); otherwise it is dropped, so the new version lists no still it can't show, and keeps its riders.
"""
import argparse, json, os, re, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PIPELINE = os.path.join(ROOT, "pipeline")
CATALOG = os.path.join(ROOT, "catalog.json")
sys.path.insert(0, PIPELINE)
import paths  # noqa: E402
import release_zip  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rebuild_choices  # noqa: E402

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
OSM_RE = re.compile(r"^((way|relation|skimap)/)?[1-9][0-9]{0,15}$")   # skimap/497: no OSM outline (FEAT-286)
RUN_ID_RE = re.compile(r"^[1-9][0-9]{0,19}$")   # FEAT-342: the Refresh packs run that started this build
REQUESTED_BY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@-]{0,127}$")   # a game account id (Firebase uid) or a login
MAX_NAME = 100
BUILD_ON = ("cloud", "pc")                      # FEAT-344: the free runner, or the self-hosted runner on Drew's PC
PC_REF = "refs/heads/main"
RETRY_BOT = "github-actions[bot]"               # build-pack-retry.yml re-runs a run as this (FEAT-314)


class Refused(Exception):
    pass


def check_inputs(name, osm_id, slug, requested_by, resorts_dir=None, rebuild=None, refresh_run=None):
    """-> dict(mode, slug, name, osm_id, requested_by, refresh_run, tier, deps). Raises Refused on bad input. `mode`
    is "rebuild" when resorts/<slug>/<slug>.json exists (name and osm_id are then optional: the config already says
    which ski area it is), else "new" (both needed). FEAT-297: `rebuild` is the form's pick from the rebuild list; a
    pack picked there is the slug (a typed slug must then be the same one), and it must already have a config.
    FEAT-342: `refresh_run` is the id of the Refresh packs run that started this one, digits only."""
    name, osm_id, slug, requested_by, rebuild, refresh_run = (
        s.strip() for s in (name or "", osm_id or "", slug or "", requested_by or "", rebuild or "", refresh_run or ""))
    if refresh_run and not RUN_ID_RE.fullmatch(refresh_run):
        raise Refused(f"refresh_run {refresh_run!r} is not a workflow run id")
    if rebuild and rebuild != rebuild_choices.NEW:
        if not SLUG_RE.fullmatch(rebuild) or len(rebuild) > 60:
            raise Refused(f"rebuild {rebuild!r} is not a pack slug")
        if slug and slug != rebuild:
            raise Refused(f"the rebuild list picked {rebuild} but the slug typed is {slug}: pick one")
        if not os.path.isfile(paths.config_path(rebuild, resorts_dir)):
            raise Refused(f"{rebuild} has no config in resorts/: it can't be rebuilt")
        slug = rebuild
    if not slug:
        raise Refused("no pack: pick one in the rebuild list, or type a slug (with name and osm_id for a new resort)")
    if not SLUG_RE.fullmatch(slug) or len(slug) > 60:
        raise Refused(f"slug {slug!r} is not lower-case letters, digits and single hyphens (at most 60)")
    if len(name) > MAX_NAME or any(ord(c) < 32 or ord(c) == 127 for c in name) or name.startswith("-"):
        raise Refused(f"name is longer than {MAX_NAME} characters, has control characters or starts with -")
    if osm_id and not OSM_RE.fullmatch(osm_id):
        raise Refused(f"osm_id {osm_id!r} is not an OSM or Skimap.org id (123, way/123, relation/123 or skimap/123)")
    if requested_by and not REQUESTED_BY_RE.fullmatch(requested_by):
        raise Refused("requested_by is not an account id (a letter or digit, then letters, digits and _.:@-, "
                      "at most 128)")
    path = paths.config_path(slug, resorts_dir)
    if os.path.isfile(path):
        cfg = json.load(open(path, encoding="utf-8"))
        if cfg.get("source_only"):
            raise Refused(f"{slug} is a relocate source (source_only), not a pack: build the resort that uses it")
        mode = "rebuild"
        name = name or cfg.get("name") or slug
    else:
        if not name or not osm_id:
            raise Refused(f"{slug} is a new resort: give both name and osm_id (the ski area picked in the game)")
        mode, cfg = "new", {}
    return {"mode": mode, "slug": slug, "name": name, "osm_id": osm_id, "requested_by": requested_by,
            "refresh_run": refresh_run, "tier": cfg.get("tier", "gold"),
            "deps": deps(slug, resorts_dir) if mode == "rebuild" else []}


def deps(slug, resorts_dir=None, seen=None):
    """the resorts whose raw data `slug` builds on, deepest first: its `raw_from` (FEAT-268) and its relocate
    sources, and theirs. A new resort has none (resort.py plan never writes either)."""
    seen = set() if seen is None else seen
    path = paths.config_path(slug, resorts_dir)
    if not os.path.isfile(path):
        raise Refused(f"{slug} names a resort with no config ({path})")
    cfg = json.load(open(path, encoding="utf-8"))
    names = ([cfg["raw_from"]] if cfg.get("raw_from") else []) + \
        [m["source"] for m in cfg.get("relocate") or [] if m.get("source")]
    out = []
    for d in dict.fromkeys(names):
        if d in seen or d == slug:
            continue
        seen.add(d)
        out += [x for x in deps(d, resorts_dir, seen) if x not in out] + [d]
    return list(dict.fromkeys(out))


def md(text):
    """`text` safe in a Markdown heading or table cell of the run summary (the name is untrusted text)"""
    return re.sub(r"([\\`*_{}\[\]<>|#!])", r"\\\1", text)


def summary(line):
    print(line, flush=True)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def outputs(values):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            for k, v in values.items():
                f.write(f"{k}={v}\n")


def stream(cmd):
    """run cmd, passing its output through as it comes -> (exit code, the output). BUG-172: a character this
    console can't show is replaced, never a failed build (the PC runner's pipe is cp1252; vite prints "✓")"""
    for out in (sys.stdout, sys.stderr):
        if hasattr(out, "reconfigure"):
            out.reconfigure(errors="replace")
    p = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                         encoding="utf-8", errors="replace", bufsize=1, env={**os.environ, "PYTHONUNBUFFERED": "1"})
    lines = []
    for line in p.stdout:
        print(line, end="", flush=True)
        lines.append(line)
    return p.wait(), "".join(lines)


def run(cmd, runner=stream):
    print("  $ " + " ".join(cmd), flush=True)   # the inputs are checked, and the LANDFIRE email is in the env only
    return runner(cmd)


def publish_result(text):
    """the run summary's word on what publish_pack did, from its output"""
    if m := re.search(r"(unchanged since v\d+)", text):
        return f"{m.group(1)}: nothing published"
    if m := re.search(r"(https://github\.com/\S+/pull/\d+) is open with this content", text):
        return f"already in {m.group(1)}: nothing published"
    if m := re.search(r"opened (https://github\.com/\S+/pull/\d+)", text):
        return f"opened {m.group(1)}"
    return "done"


def py(script, *args):
    return [sys.executable, os.path.join(PIPELINE, script), *args]


def stage_commands(stage, cfg):
    """the commands one stage runs, in order"""
    slug = cfg["slug"]
    if stage == "resolve":
        if cfg["mode"] == "rebuild":
            return []
        # --alone: the area picked in the game is the pack; a neighbour sold with it (Boston Mills and Brandywine)
        # is a hand config's job. --osm names it, so resolve never asks which of several areas.
        return [py("resort.py", "add", "--osm", cfg["osm_id"], "--slug", slug, "--alone", "--stop-after", "plan",
                   "--", cfg["name"])]    # after --: a name is never read as a flag
    if stage == "fetch":
        return [py("build_resort.py", d, "--stop-after", "grooming") for d in cfg["deps"]] + \
               [py("build_resort.py", slug, "--stop-after", "grooming")]
    if stage == "build":
        return [py("build_resort.py", slug, "--from", "build", "--stop-after", "index")]
    if stage == "report":
        # BUG-124: from `published` (FEAT-293), the stage before the report: the resort's figures for line 21
        return [py("build_resort.py", slug, "--from", "published", "--stop-after", "report")]
    if stage == "publish":
        cmd = py("publish_pack.py", os.path.join(paths.PACKS, slug), "--tier", cfg["tier"])
        if cfg.get("run_url"):
            cmd += ["--run-url", cfg["run_url"]]
        if cfg.get("requested_by"):
            cmd += [f"--requested-by={cfg['requested_by']}"]     # one word: never read as a flag
        if cfg.get("refresh_url"):
            cmd += ["--refresh-run", cfg["refresh_url"]]
        return [cmd]
    raise ValueError(stage)


def maintainers(repo_dir=ROOT):
    """.github/maintainers.txt: one login a line, # comments (publish_pack.maintainers, without its imports)"""
    path = os.path.join(repo_dir, ".github", "maintainers.txt")
    if not os.path.isfile(path):
        return set()
    with open(path, encoding="utf-8") as f:
        return {line.split("#")[0].strip() for line in f} - {""}


def where(env, trusted):
    """FEAT-344: -> "cloud" or "pc", the runner the build job takes. Raises Refused for a PC run that is not a
    workflow_dispatch on main started by a maintainer. The repo is public: the PC runner must never take a pull
    request's code or a branch's edited workflow. The build job's `if:` checks the event and the ref again, and the
    runner's own job-started hook on the PC (tools/pc-runner/job_started.ps1, copied outside any checkout) checks
    all of it where no workflow edit can reach. A re-run by build-pack-retry.yml has github-actions[bot] as its
    triggering actor; the person who started the run is then GITHUB_ACTOR, who must be a maintainer (as in
    publish_pack.publisher_login)."""
    on = (env.get("BUILD_ON") or "cloud").strip()
    if on not in BUILD_ON:
        raise Refused(f"build_on {on!r} is not one of {', '.join(BUILD_ON)}")
    if on == "cloud":
        return on
    actor = env.get("GITHUB_ACTOR", "")
    by = env.get("GITHUB_TRIGGERING_ACTOR") or actor
    why = []
    if env.get("GITHUB_EVENT_NAME") != "workflow_dispatch":
        why.append(f"the event is {env.get('GITHUB_EVENT_NAME')!r}, not workflow_dispatch")
    if env.get("GITHUB_REF") != PC_REF:
        why.append(f"the ref is {env.get('GITHUB_REF')!r}, not {PC_REF}")
    if actor not in trusted:
        why.append(f"{actor or 'nobody'} is not in .github/maintainers.txt")
    if by not in (actor, RETRY_BOT) and by not in trusted:
        why.append(f"{by} (who re-ran it) is not in .github/maintainers.txt")
    if why:
        raise Refused("a build on Drew's PC runs only a workflow_dispatch on main by a maintainer: " + "; ".join(why))
    return on


def data_slug(slug, resorts_dir=None):
    """-> (the folder its raw data is in, its config): `raw_from` (FEAT-268), else the slug; (slug, {}) with no config"""
    path = paths.config_path(slug, resorts_dir)
    if not os.path.isfile(path):
        return slug, {}
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg.get("raw_from") or slug, cfg


def raw_score(root, data, cfg):
    """how many of the raw layers `cfg` builds on are already in <root>/<data>/ (build_resort.raw_need's folders,
    plus the OSM ski file): the root holding most of them is the one the fetch tops up, not fetches again"""
    if not cfg:
        return 0
    import build_resort
    have = sum(1 for folder, _ in build_resort.raw_need(cfg).values() if os.path.isdir(os.path.join(root, data, folder)))
    return have + os.path.isfile(os.path.join(root, data, "osm", "ski.json"))


def pick_raw_root(roots, cfg, resorts_dir=None):
    """FEAT-344: on Drew's PC the raw data is in more than one folder (Vail's in Documents/snowboard-sim/raw, the
    rest in SnowboardAnywhere/raw). -> (root, note): the root that holds most of the resort's raw layers, the first
    on a tie (a new resort: the first). Raises Refused when a resort it builds on (`deps`: raw_from, relocate
    sources) has its data only in another root, since the fetch would then download that resort again."""
    if not roots:
        raise Refused("SBA_RAW_ROOTS is empty: set it in the runner's .env (docs/pc-runner.md)")
    data, own = data_slug(cfg["slug"], resorts_dir)
    scores = [raw_score(r, data, own) for r in roots]
    best = max(range(len(roots)), key=lambda i: (scores[i], -i))
    root = roots[best]
    for d in cfg["deps"]:
        dd, dcfg = data_slug(d, resorts_dir)
        elsewhere = [r for r in roots if r != root and raw_score(r, dd, dcfg)]
        if not raw_score(root, dd, dcfg) and elsewhere:
            raise Refused(f"{cfg['slug']}'s raw data is in {root} but {d}'s is in {elsewhere[0]}: move one so they "
                          f"share a root, or the fetch downloads {d} again")
    note = f"{data} has {scores[best]} raw layers there" if scores[best] else "no raw data yet: it is fetched there"
    return root, note


def env_out(values):
    """set variables for the job's later steps ($GITHUB_ENV)"""
    path = os.environ.get("GITHUB_ENV")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            for k, v in values.items():
                f.write(f"{k}={v}\n")


def pc_setup(cfg, env, resorts_dir=None):
    """FEAT-344: the variables the build steps get on Drew's PC -> ({name: value}, note). SBA_RAW_ROOTS (the
    runner's .env) lists the raw roots, os.pathsep between; GAME_CHECKOUT is the game's main, checked out by the
    job. Raises Refused when the runner is not set up (docs/pc-runner.md)."""
    roots = [os.path.abspath(r.strip()) for r in (env.get("SBA_RAW_ROOTS") or env.get("SBA_RAW_ROOT") or "")
             .split(os.pathsep) if r.strip()]
    missing = [r for r in roots if not os.path.isdir(r)]
    if missing:
        raise Refused(f"raw root {missing[0]} (SBA_RAW_ROOTS) is not a folder")
    root, note = pick_raw_root(roots, cfg, resorts_dir)
    game = os.path.abspath(env.get("GAME_CHECKOUT") or ".")
    if not paths.has_game(game):
        raise Refused(f"no game checkout at {game} (GAME_CHECKOUT): the attract and spots stages need it")
    # the OpenSkiData index (about 800 MB) stays in one place whichever root the raw data is in
    return {"SBA_RAW_ROOT": root, "SBA_GAME_REPO": game,
            "SBA_INDEX_DIR": env.get("SBA_INDEX_DIR") or os.path.join(roots[0], "_index")}, note


def published_pack(slug, catalog_path=None):
    """the catalog's `pack` for resort `slug` ({url, bytes, content, ...}), or None"""
    try:
        with open(catalog_path or CATALOG, encoding="utf-8") as f:
            catalog = json.load(f)
    except (OSError, ValueError):
        return None
    e = next((r for r in catalog.get("resorts") or [] if r.get("slug") == slug), None)
    return (e or {}).get("pack") or None


def carry_menu(slug, pack_dir, pack, carry=None):
    """FEAT-345: the published menu into the fresh pack folder before the build -> a line for the run summary.
    Never raises: a menu that can't be carried leaves the build as it was before (shots, no still, no takes)."""
    carry = carry or release_zip.carry_attract
    if not pack or not pack.get("url"):
        print(f"  menu: {slug} has no published pack: nothing to carry", flush=True)
        return "no published menu"
    try:
        got = carry(pack["url"], int(pack.get("bytes") or 0), pack_dir, log=lambda t: print(t, flush=True))
    except Exception as e:      # any failure: build on without it
        print(f"::warning::menu not carried over, building without it: {e}", flush=True)
        return f"menu not carried ({e})"
    print(f"  menu: {'carried' if got['carried'] else 'nothing carried'}: {got['why']}", flush=True)
    return f"menu carried ({got['why']})" if got["carried"] else f"no menu carried ({got['why']})"


def settle_stills(pack_dir, pack):
    """FEAT-345: after the build, a menu still the game would not show for this build (`gen_content.stale_stills`)
    stays only when the pack is the published one (same content key: nothing publishes, the published still stays
    right); otherwise it goes, so no version lists a still it can't show -> a line for the run summary, or ''"""
    import gen_content
    try:
        stale = gen_content.stale_stills(pack_dir)
    except (OSError, ValueError) as e:
        return f"stills not checked ({e})"
    if not stale:
        return ""
    from publish_pack import content_key
    key, published = content_key(pack_dir), (pack or {}).get("content")
    if published and key == published:
        print(f"  menu: the pack is the published one (content {key}): its still stays", flush=True)
        return "the pack is unchanged: still kept"
    gen_content.drop_stills(pack_dir, f"rendered from another build, and this pack is not the published one "
                            f"(content {key}, published {published or 'with no content key'}): a GPU renders a new "
                            f"one (build_resort.py <slug> --force attract on Drew's PC)", only=stale,
                            log=lambda t: print(t, flush=True))
    return "the pack changed: still dropped (riders kept), a GPU renders a new one"


def from_env():
    return check_inputs(os.environ.get("NAME"), os.environ.get("OSM_ID"), os.environ.get("SLUG"),
                        os.environ.get("REQUESTED_BY"), rebuild=os.environ.get("REBUILD"),
                        refresh_run=os.environ.get("REFRESH_RUN"))


def main(argv=None, runner=stream, carry=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("stage", choices=["check", "where", "pc-setup", "inputs", "resolve", "fetch", "build", "report",
                                      "publish"])
    a = ap.parse_args(argv)
    try:
        cfg = from_env()
    except Refused as e:
        summary(f"**Refused:** {e}")
        return 1
    if a.stage == "check":
        print(f"{cfg['slug']}: {cfg['mode']}" + (f", builds on {', '.join(cfg['deps'])}" if cfg["deps"] else ""))
        return 0
    if a.stage in ("where", "pc-setup"):
        try:
            if a.stage == "where":
                on = where(os.environ, maintainers())
                outputs({"runner": on})
                print(f"{cfg['slug']}: builds on " + ("the free runner" if on == "cloud" else "Drew's PC"))
                return 0
            values, note = pc_setup(cfg, os.environ)
        except Refused as e:
            summary(f"**Refused:** {e}")
            return 1
        env_out(values)
        print("\n".join(f"{k}={v}" for k, v in values.items()))
        summary(f"Built on Drew's PC: raw data in `{values['SBA_RAW_ROOT']}` ({note}).\n")
        return 0
    if a.stage == "inputs":
        outputs({"mode": cfg["mode"], "slug": cfg["slug"]})
        summary(f"## {md(cfg['name'])} (`{cfg['slug']}`)\n\n"
                + ("New resort, OSM " + cfg["osm_id"] if cfg["mode"] == "new" else "Rebuild of the committed config")
                + (f", builds on {', '.join(cfg['deps'])}" if cfg["deps"] else "")
                + (f". Requested by `{cfg['requested_by']}`" if cfg["requested_by"] else "")
                + (f", started by Refresh packs run {cfg['refresh_run']}" if cfg["refresh_run"] else "") + ".\n\n"
                "| stage | result | time |\n|---|---|---|")
        return 0
    cfg["run_url"] = os.environ.get("RUN_URL")
    if cfg["refresh_run"]:
        server = os.environ.get("GITHUB_SERVER_URL") or "https://github.com"
        cfg["refresh_url"] = f"{server}/{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/{cfg['refresh_run']}"
    cmds = stage_commands(a.stage, cfg)
    if not cmds:
        summary(f"| {a.stage} | skip: the config is committed | |")
        return 0
    t0 = time.time()
    text, notes = "", []
    pack_dir, pack = os.path.join(paths.PACKS, cfg["slug"]), None
    if a.stage == "build" and (os.environ.get("BUILD_ON") or "cloud").strip() == "cloud":
        pack = published_pack(cfg["slug"])
        notes.append(carry_menu(cfg["slug"], pack_dir, pack, carry))
    for cmd in cmds:
        code, out = run(cmd, runner)
        text += out
        if code:
            summary(f"| {a.stage} | **failed** (exit {code}) | {time.time() - t0:.0f} s |")
            return code
    if pack is not None and os.path.isfile(os.path.join(pack_dir, "meta.json")):
        notes.append(settle_stills(pack_dir, pack))
    if a.stage == "fetch":         # FEAT-348: what the OSM change check found (build_resort.plan_osm, fetch_run)
        notes += re.findall(r"^(?:::warning::|\s*(?:warning: )?)(osm: .*)$", text, re.M)
    result = publish_result(text) if a.stage == "publish" else "done"
    result += "".join(f"; {md(n)}" for n in notes if n)
    summary(f"| {a.stage} | {result} | {time.time() - t0:.0f} s |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
