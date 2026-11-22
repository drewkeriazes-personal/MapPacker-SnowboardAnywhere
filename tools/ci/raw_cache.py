"""FEAT-346: the free runner's raw-data cache. The runner starts with an empty raw folder, and the published pack
holds only the built output, so without this every rebuild downloads every layer again (2 to 3.3 GB and up to
3,700 requests per resort).

    python tools/ci/raw_cache.py restore    before the fetch stage: each raw folder the build reads, from its cache
    python tools/ci/raw_cache.py save       after the fetch stage: each one whose data changed, to its cache

The run's slug comes from the environment, checked as build_pack_ci.py checks it. The folders are the slug's raw
folder and those of the resorts it builds on (`raw_from`, relocate sources: build_pack_ci.deps).

Each raw folder's cache is the **draft** release `raw/<folder>`. A draft is visible only to accounts that can push,
has no git tag, and is not a pack release (releases.parse_tag reads only `<slug>/v<N>`), so the catalog,
RELEASES.md and publish_pack's next version never see it. Its assets:
    cache.json         {"key", "parts": [{"name", "size", "sha256"}]}: the set restore reads
    <key>.tar.NNN      a plain tar of the folder (TIFF and LAZ are compressed already), split at PART bytes, under
                       the 2 GiB asset limit
`key` is a hash of the data files (path and size) and fetch_index.json (pipeline/fetch_index.py: what each file
was fetched for); logs and stage state are saved but left out of it, so a restored folder that downloaded nothing
new uploads nothing. The fetch stage then decides what to fetch again: build_resort.py's stage state skips a
manifest that didn't change, and fetch_index.prune fetches again only the items whose key changed.

restore streams each part into tarfile (filter "data": no absolute paths, no `..`, no links out of the folder) and
checks its size and sha256; on any mismatch or error it empties the folder, so the fetch starts fresh. save writes
and uploads one part at a time (the disk holds one part, not a second copy of the folder), then cache.json, then
deletes the parts the previous cache.json named: a save that dies halfway leaves the previous set whole (its own
parts stay as orphans until a later save of the same key overwrites them).
Neither ever fails the build: a miss or any error is a warning, and the fetch downloads what is missing.
FRESH_DATA=true (Build pack's `fresh_data`) skips the restore, so everything is downloaded again and saved.
Env: GH_TOKEN (the App's, contents: write: drafts need push access), GH_REPO, SBA_RAW_ROOT."""
import argparse, hashlib, json, os, shutil, subprocess, sys, tarfile, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_pack_ci  # noqa: E402
sys.path.insert(0, build_pack_ci.PIPELINE)
import fetch_index  # noqa: E402
import paths  # noqa: E402

PART = 1 << 30
CACHE = "cache.json"
UNSAVED = {"fetch_log.txt", "env.txt"}                                  # this run's logs
UNKEYED = UNSAVED | {"build_resort.json", "FETCH_COMPLETE.txt"}         # saved, but not data
CHUNK = 1 << 20


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
    return f"restored {size / 2**20:,.0f} MB (key {cache['key']})"


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
    if not (os.path.isdir(raw) and os.path.isfile(os.path.join(raw, "FETCH_COMPLETE.txt"))):
        return "skip: no finished fetch in the folder"
    files = saved_files(raw)
    key = data_key(raw, files)
    old = read_cache(folder)
    if old and old.get("key") == key:
        return f"skip: the cache already holds this data (key {key})"
    if old is None:
        try:
            gh("release", "view", tag(folder), "--json", "isDraft")
        except RuntimeError:
            gh("release", "create", tag(folder), "--draft", "--title", f"Raw data cache: {folder}",
               "--notes", "FEAT-346: the free runner's raw-data cache (tools/ci/raw_cache.py). A draft on purpose: "
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
        new = {"key": key, "parts": writer.parts}
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
    return f"saved {size / 2**20:,.0f} MB in {len(writer.parts)} part(s) (key {key})"


# ------------------------------------------------------------------------------------------------ the run

def folders(slug: str, dep_slugs: list[str]) -> list[str]:
    """the raw folders a build of `slug` reads: its own (or its raw_from) and those of the resorts it builds on"""
    return list(dict.fromkeys(build_pack_ci.data_slug(s)[0] for s in [*dep_slugs, slug]))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("action", choices=["restore", "save"])
    a = ap.parse_args(argv)
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
