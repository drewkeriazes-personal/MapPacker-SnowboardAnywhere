"""FEAT-346: the free runner's raw-data cache. The runner starts with an empty raw folder, and the published pack
holds only the built output, so without this every rebuild downloads every layer again (2 to 3.3 GB and up to
3,700 requests per resort).

    python tools/ci/raw_cache.py restore    before the fetch stage: each raw folder the build reads, from its cache
    python tools/ci/raw_cache.py save       after the fetch stage: each one whose data changed, to its cache
    python tools/ci/raw_cache.py covered --out FILE
                                            FEAT-347, in the probe job: FILE when the cache covers the build

The run's slug comes from the environment, checked as build_pack_ci.py checks it. The folders are the slug's raw
folder and those of the resorts it builds on (`raw_from`, relocate sources: build_pack_ci.deps).

Each raw folder's cache is the **draft** release `raw/<folder>`. A draft is visible only to accounts that can push,
has no git tag, and is not a pack release (releases.parse_tag reads only `<slug>/v<N>`), so the catalog,
RELEASES.md and publish_pack's next version never see it. Its assets:
    cache.json         {"key", "stages", "parts": [{"name", "size", "sha256"}]}: the set restore reads;
                       `stages` holds the folder's build_resort.json fingerprints of the data stages
                       (build_resort.DATA_STAGES; `fetch` is the manifest_items_sha of the manifest the fetch used)
    <key>.tar.NNN      a plain tar of the folder (TIFF and LAZ are compressed already), split at PART bytes, under
                       the 2 GiB asset limit
`key` is a hash of the data files (path and size), fetch_index.json (pipeline/fetch_index.py: what each file
was fetched for) and `stages`; logs and the later stages' state are saved but left out of it, so a restored folder
that downloaded nothing new uploads nothing, and the build_resort.json a restore puts back is the one `stages` names. The fetch stage then decides what to fetch again: build_resort.py's stage state skips a
manifest that didn't change, and fetch_index.prune fetches again only the items whose key changed.

restore streams each part into tarfile (filter "data": no absolute paths, no `..`, no links out of the folder) and
checks its size and sha256; on any mismatch or error it empties the folder, so the fetch starts fresh. save writes
and uploads one part at a time (the disk holds one part, not a second copy of the folder), then cache.json, then
deletes the parts the previous cache.json named: a save that dies halfway leaves the previous set whole (its own
parts stay as orphans until a later save of the same key overwrites them).
Neither ever fails the build: a miss or any error is a warning, and the fetch downloads what is missing.
FRESH_DATA=true (Build pack's `fresh_data`) skips the restore, so everything is downloaded again and saved.
FEAT-349: a fetch that failed on some items is saved too (`"complete": false`, and part of the key): the fetch
stage records fetch_index.json for the files it has and removes FETCH_COMPLETE.txt, so a retry restores them and
downloads only the rest. A partial never replaces a complete cache, and never covers a build.

covered (FEAT-347) reads only each folder's cache.json, never a part. A folder is covered when its `stages` are the
data stages' fingerprints on this checkout of main (build_resort.py would skip every one of them on the restored
folder: the same config, node lists, MANIFEST_VERSION and manifest items) and the node lists and manifest are
there. When every folder the build reads is covered and the run restores (a rebuild, on the free runner,
FRESH_DATA not true), FILE gets {"covers": [folders], "keep": STILL_NEEDED}, and probe_hosts.py --raw-cache FILE
lets every other host warn instead of fail. Anything else (a new resort, a changed manifest, no cache, any error)
writes no FILE, and the probe is as before. Overpass warns with the rest: FEAT-348's change check
and a failed fetch of OpenStreetMap again keep the cached copy, so a covered build never needs it.
Env: GH_TOKEN (the App's, contents: write: drafts need push access), GH_REPO, SBA_RAW_ROOT."""
import argparse, hashlib, json, os, shutil, subprocess, sys, tarfile, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_pack_ci  # noqa: E402
sys.path.insert(0, build_pack_ci.PIPELINE)
import build_resort  # noqa: E402
import fetch_index  # noqa: E402
import paths  # noqa: E402

PART = 1 << 30
CACHE = "cache.json"
UNSAVED = {"fetch_log.txt", "env.txt"}                                  # this run's logs
UNKEYED = UNSAVED | {"build_resort.json", fetch_index.COMPLETE}         # saved, but not data
CHUNK = 1 << 20
# FEAT-347: the probed hosts a covered rebuild still calls. With every data stage skipped (nodes: ept_select.py;
# manifest: gen_manifest.py, offline; fetch: fetch.ps1; landfire: fetch_landfire.mjs, whose clips are in the raw
# folder; grooming: fetch_grooming.py, likewise), only the published stage reaches a probed host: OpenSkiData's
# index (published.py through resort.index_file). build_pack.py, gen_content.py, pack_content.py and pack_report.py
# read local files; the menu carry, publish and this cache are GitHub. resolve and plan (resort.py: Geofabrik,
# Entwine, TNM, WESM, STAC, Mapterhorn attribution) run only for a new resort, which is never covered.
STILL_NEEDED = ("tiles.openskimap.org",)


def tag(folder: str) -> str:
    return f"raw/{folder}"


def gh(*args: str) -> str:
    r = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        raise RuntimeError(f"gh {' '.join(args[:3])} failed: {(r.stderr or r.stdout).strip()[:300]}")
    return r.stdout


# ------------------------------------------------------------------------------------------------ the folder

def saved_files(raw: str) -> list[str]:
    """the folder's files to save, relative and with /, sorted (no logs, no partial downloads)"""
    out = []
    for d, _, names in os.walk(raw):
        for n in names:
            if n.endswith((".part", ".tmp", ".keep")) or (d == raw and n in UNSAVED):
                continue
            out.append(os.path.relpath(os.path.join(d, n), raw).replace(os.sep, "/"))
    return sorted(out)


def stages(raw: str) -> dict:
    """the data stages' input fingerprints in the folder's build_resort.json ({} without one)"""
    try:
        with open(os.path.join(raw, build_resort.STATE), encoding="utf-8") as f:
            state = json.load(f)
    except (OSError, ValueError):
        return {}
    return {s: state[s] for s in build_resort.DATA_STAGES if s in state} if isinstance(state, dict) else {}


def data_key(raw: str, files: list[str]) -> str:
    h = hashlib.sha256()
    for rel in files:
        if rel not in UNKEYED:
            h.update(f"{rel}\0{os.path.getsize(os.path.join(raw, rel))}\n".encode())
    try:
        with open(os.path.join(raw, fetch_index.INDEX), "rb") as f:
            h.update(f.read())
    except OSError:
        pass
    h.update(json.dumps(stages(raw), sort_keys=True).encode())
    h.update(b"complete" if fetch_index.COMPLETE in files else b"partial")    # FEAT-349: a partial is its own key
    return h.hexdigest()[:16]


# ------------------------------------------------------------------------------------------------ the release

def read_cache(folder: str) -> dict | None:
    """the release's cache.json; None when there is no release or no cache.json yet"""
    try:
        names = json.loads(gh("release", "view", tag(folder), "--json", "assets", "--jq", "[.assets[].name]"))
    except RuntimeError:
        return None
    if CACHE not in names:
        return None
    return json.loads(gh("release", "download", tag(folder), "-p", CACHE, "-O", "-"))


def open_part(folder: str, name: str) -> subprocess.Popen:
    """a download of one asset to a pipe (stdout), read as it arrives"""
    return subprocess.Popen(["gh", "release", "download", tag(folder), "-p", name, "-O", "-"], stdout=subprocess.PIPE)


class Parts:
    """a readable stream of the parts, each downloaded as it is read and checked at its end"""

    def __init__(self, folder: str, parts: list[dict]):
        self.folder, self.todo, self.proc, self.part = folder, list(parts), None, None

    def _start(self) -> bool:
        if not self.todo:
            return False
        self.part = self.todo.pop(0)
        self.proc = open_part(self.folder, self.part["name"])
        self.sha, self.got = hashlib.sha256(), 0
        return True

    def _finish(self):
        self.proc.stdout.close()
        failed, self.proc = self.proc.wait(), None
        if failed:
            raise RuntimeError(f"download of {self.part['name']} failed")
        if self.got != self.part["size"] or self.sha.hexdigest() != self.part["sha256"]:
            raise RuntimeError(f"{self.part['name']}: size or sha256 is not cache.json's")

    def read(self, n: int = -1) -> bytes:
        """the next bytes; b"" once every part is read and checked"""
        while self.proc or self._start():
            data = self.proc.stdout.read(n if n > 0 else CHUNK)
            if data:
                self.sha.update(data)
                self.got += len(data)
                return data
            self._finish()
        return b""


def restore_one(folder: str, raw: str) -> str:
    if os.path.isdir(raw) and os.listdir(raw):
        return "skip: the folder already has data"
    cache = read_cache(folder)
    if not cache:
        return "miss: no cache yet"
    os.makedirs(raw, exist_ok=True)
    try:
        stream = Parts(folder, cache["parts"])
        with tarfile.open(fileobj=stream, mode="r|") as tar:
            tar.extractall(raw, filter="data")
        while stream.read():        # the tar's end padding, then the last part's check
            pass
    except Exception:
        shutil.rmtree(raw, ignore_errors=True)
        raise
    size = sum(p["size"] for p in cache["parts"])
    return f"restored {size / 2**20:,.0f} MB{'' if cache.get('complete', True) else ', partial'} (key {cache['key']})"


class PartWriter:
    """a writable stream that cuts the tar into PART-byte files and hands each one to `done` when it is full"""

    def __init__(self, workdir: str, key: str, done):
        self.workdir, self.key, self.done, self.parts, self.f = workdir, key, done, [], None

    def _open(self):
        name = f"{self.key}.tar.{len(self.parts):03d}"
        self.f, self.sha, self.size = open(os.path.join(self.workdir, name), "wb"), hashlib.sha256(), 0
        self.parts.append({"name": name})

    def _close(self):
        self.f.close()
        self.parts[-1].update(size=self.size, sha256=self.sha.hexdigest())
        self.done(os.path.join(self.workdir, self.parts[-1]["name"]))
        self.f = None

    def write(self, data: bytes) -> int:
        view = memoryview(data)
        while view:
            if self.f is None:
                self._open()
            n = min(len(view), PART - self.size)
            self.f.write(view[:n])
            self.sha.update(view[:n])
            self.size += n
            view = view[n:]
            if self.size == PART:
                self._close()
        return len(data)

    def close(self):
        if self.f is not None:
            self._close()


def save_one(folder: str, raw: str) -> str:
    complete = os.path.isfile(os.path.join(raw, fetch_index.COMPLETE))
    if not (complete or os.path.isfile(os.path.join(raw, fetch_index.INDEX))):
        return "skip: no fetch in the folder"       # FEAT-349: a partial fetch is saved only with its index
    files = saved_files(raw)
    key = data_key(raw, files)
    old = read_cache(folder)
    if old and old.get("key") == key:
        return f"skip: the cache already holds this data (key {key})"
    if not complete and old and old.get("complete", True):
        return "skip: a partial fetch never replaces a complete cache"
    if old is None:
        try:
            gh("release", "view", tag(folder), "--json", "isDraft")
        except RuntimeError:
            gh("release", "create", tag(folder), "--draft", "--title", f"Raw data cache: {folder}",
               "--notes", "The free runner's raw-data cache (tools/ci/raw_cache.py). A draft on purpose: "
               "never publish it.")

    def upload(path):
        gh("release", "upload", tag(folder), path, "--clobber")
        os.remove(path)

    with tempfile.TemporaryDirectory(dir=os.environ.get("RUNNER_TEMP")) as work:
        writer = PartWriter(work, key, upload)
        with tarfile.open(fileobj=writer, mode="w|", format=tarfile.PAX_FORMAT) as tar:
            for rel in files:
                tar.add(os.path.join(raw, rel), arcname=rel, recursive=False)
        writer.close()
        new = {"key": key, "complete": complete, "stages": stages(raw), "parts": writer.parts}
        cache_path = os.path.join(work, CACHE)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(new, f, indent=1)
        gh("release", "upload", tag(folder), cache_path, "--clobber")
    # only the set cache.json named before: a save of the same folder running at the same time (two builds on one
    # raw_from source) keeps its parts, and whichever cache.json lands last names a whole set
    keep = {p["name"] for p in writer.parts}
    for p in (old or {}).get("parts", []):
        if p["name"] not in keep:
            gh("release", "delete-asset", tag(folder), p["name"], "--yes")
    size = sum(p["size"] for p in writer.parts)
    return f"saved {size / 2**20:,.0f} MB in {len(writer.parts)} part(s){'' if complete else ', partial'} (key {key})"


# ------------------------------------------------------------------------------------------------ coverage

def uncovered(folder: str, cache: dict | None, resorts_dir=None, manifests_dir=None) -> str | None:
    """FEAT-347: None when `cache` (the folder's cache.json) covers a build of `folder` from this checkout, so the
    restored folder skips every data stage and downloads nothing; else why it does not"""
    if not cache:
        return "no cache yet"
    if not cache.get("complete", True):
        return "the cache is from a fetch that did not finish"      # FEAT-349
    if not os.path.isfile(paths.config_path(folder, resorts_dir)):
        return "no config"
    recorded = cache.get("stages") or {}
    r = build_resort.Resort(folder, os.path.join(paths.raw_root(), folder), os.path.join(paths.PACKS, folder),
                            resorts_dir, manifests_dir)
    for stage in build_resort.DATA_STAGES:
        inputs, present, _ = build_resort.STAGE_FN[stage]
        if stage not in recorded:
            return f"the cache has no {stage} fingerprint"
        if recorded[stage] != inputs(r):
            return "the manifest changed" if stage == "fetch" else f"the {stage} stage's inputs changed"
        if stage in ("nodes", "manifest") and not present(r):     # in git: the build would make them again
            return f"the {stage} stage would run again"
    return None


def covered(out: str) -> list[str]:
    """the folders the cache covers, written to `out` when it covers them all; [] (and no `out`) otherwise"""
    if os.path.exists(out):
        os.remove(out)
    why = None
    if (os.environ.get("FRESH_DATA") or "").strip().lower() == "true":
        why = "fresh data asked for"
    elif (os.environ.get("BUILD_ON") or "cloud").strip() != "cloud":
        why = "the build runs on Drew's PC, which restores nothing"
    if why:
        build_pack_ci.summary(f"Raw cache not used ({why}): every data host is required.\n")
        return []
    try:
        cfg = build_pack_ci.from_env()
        if cfg["mode"] != "rebuild":
            build_pack_ci.summary("Raw cache: a new resort has none, so every data host is required.\n")
            return []
        names = folders(cfg["slug"], cfg["deps"])
    except (build_pack_ci.Refused, OSError, ValueError) as e:
        build_pack_ci.summary(f"Raw cache not checked ({build_pack_ci.md(str(e))}): every data host is required.\n")
        return []
    gaps = []
    for folder in names:
        try:
            cache = read_cache(folder)
            why = uncovered(folder, cache)
        except Exception as e:      # any error: not covered, and the probe is as before
            why = f"not read: {e}"
        if why:
            gaps.append(f"{folder} ({why})")
    if gaps:
        build_pack_ci.summary(f"Raw cache does not cover {build_pack_ci.md(', '.join(gaps))}: every data host is "
                              "required.\n")
        return []
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"covers": names, "keep": list(STILL_NEEDED)}, f)
    build_pack_ci.summary(f"Raw cache covers {', '.join(names)}: the build fetches nothing.\n")
    return names


# ------------------------------------------------------------------------------------------------ the run

def folders(slug: str, dep_slugs: list[str]) -> list[str]:
    """the raw folders a build of `slug` reads: its own (or its raw_from) and those of the resorts it builds on"""
    return list(dict.fromkeys(build_pack_ci.data_slug(s)[0] for s in [*dep_slugs, slug]))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("action", choices=["restore", "save", "covered"])
    ap.add_argument("--out", help="covered: the file probe_hosts.py --raw-cache reads")
    a = ap.parse_args(argv)
    if a.action == "covered":
        if not a.out:
            ap.error("covered needs --out FILE")
        covered(a.out)
        return 0
    if a.action == "restore" and (os.environ.get("FRESH_DATA") or "").strip().lower() == "true":
        build_pack_ci.summary("| restore | skip: fresh data asked for | |")
        return 0
    try:
        cfg = build_pack_ci.from_env()
        names = folders(cfg["slug"], cfg["deps"])
    except (build_pack_ci.Refused, OSError, ValueError) as e:
        print(f"::warning::raw cache: {e}")
        return 0
    root = paths.raw_root()
    for folder in names:
        raw = os.path.join(root, folder)
        try:
            result = (restore_one if a.action == "restore" else save_one)(folder, raw)
        except Exception as e:       # never fails the build: a miss means a fresh fetch, a failed save a later one
            result = f"failed, {'fetching fresh' if a.action == 'restore' else 'not saved'}: {e}"
            print(f"::warning::raw cache {a.action} {folder}: {e}")
        build_pack_ci.summary(f"| {a.action} | {folder}: {build_pack_ci.md(result)} | |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
