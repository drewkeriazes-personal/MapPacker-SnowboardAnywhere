"""Reading a published pack's release zip by HTTP range requests, without downloading it (FEAT-342, FEAT-345).

`RangeFile` is a seekable file over range requests for `zipfile`: opening the zip fetches the end of its central
directory and the directory, and each member read fetches that member, a few requests for a 60 to 245 MB pack.

- `published_attract(url, size)`: the published pack's `attract/index.json` (Refresh packs, `tools/ci/refresh_packs.py`).
- `carry_attract(url, size, pack_dir)`: the published pack's generated menu (`attract/`: `index.json`, `shots.json`,
  the stills and ghost takes it lists) into a fresh build's pack folder, before the content stage of a cloud build
  (`tools/ci/build_pack_ci.py build`, FEAT-345). `gen_content.py write_attract` then keeps it when the new shots are
  the same and drops it when they are not, as it does on Drew's PC where the old pack is already in `packs/<slug>/`.
"""
import json
import os
import shutil
import tempfile
import urllib.request
import zipfile
from typing import Callable

ATTRACT = "attract/index.json"          # the zip has the pack's files at its root
CARRY_MAX_BYTES = 32 * 1024 * 1024      # a published attract/ is 1 to 4 MB; more is not a menu
USER_AGENT = "mappacker-release-zip"


class RangeFile:
    """a read-only, seekable file over HTTP range requests, for zipfile: reading one member of a release zip fetches
    the end of the central directory, the directory and that member, a few requests, not the whole pack"""

    def __init__(self, url: str, size: int, opener: Callable | None = None):
        self.url, self.size, self.pos, self.opener = url, size, 0, opener

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off if whence == 1 else self.size + off
        return self.pos

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        if n <= 0 or self.pos >= self.size:
            return b""
        end = min(self.size, self.pos + n) - 1
        req = urllib.request.Request(self.url, headers={"Range": f"bytes={self.pos}-{end}", "User-Agent": USER_AGENT})
        with (self.opener or urllib.request.urlopen)(req, timeout=60) as r:
            if getattr(r, "status", 206) != 206:
                raise OSError(f"no range answer from {self.url} (HTTP {getattr(r, 'status', '?')})")
            data = r.read()
        self.pos += len(data)
        return data


def open_release(url: str, size: int) -> zipfile.ZipFile:
    """the release zip at `url` (`size` bytes, the catalog's `bytes`), read by ranges; raises OSError"""
    if size <= 0:
        raise OSError("the catalog has no size for it")
    try:
        return zipfile.ZipFile(RangeFile(url, size))
    except (zipfile.BadZipFile, ValueError) as e:
        raise OSError(f"{url}: {e}") from e


def published_attract(url: str, size: int) -> dict | None:
    """the published pack's attract/index.json, or None when it has no attract/; raises OSError when it can't read"""
    try:
        with open_release(url, size) as z:
            return json.loads(z.read(ATTRACT)) if ATTRACT in z.namelist() else None
    except (zipfile.BadZipFile, ValueError, KeyError) as e:
        raise OSError(f"{url}: {e}") from e


def attract_files(index: dict) -> list[str]:
    """the attract/ files a generated index.json names: index.json, shots.json, each still's jpg and each take"""
    names = ["index.json", "shots.json"] + [f"{s}.jpg" for s in index.get("stills") or []] + \
        list(index.get("ghosts") or [])
    out = []
    for n in names:
        if not isinstance(n, str) or os.path.basename(n) != n or n in ("", ".", "..") or n in out:
            raise ValueError(f"attract/index.json names {n!r}, not a file in attract/")
        out.append(n)
    return out


def carry_attract(url: str, size: int, pack_dir: str, log=print) -> dict:
    """copy the published pack's generated menu into `pack_dir`/attract/ -> {"carried": bool, "why": text, ...}.

    Carried only when the published attract/index.json is generated (a hand-made menu comes from resorts/<slug>/
    with every build) and lists a still or a ghost take (else there is nothing a cloud build can't make itself), and
    `pack_dir` has no attract/ yet. Every listed file must be in the zip, or nothing is carried. Raises OSError when
    the release can't be read; the caller logs it and builds on without (the menu then goes as a cloud build makes
    it: the shots, no still, no takes)."""
    dest = os.path.join(pack_dir, "attract")
    if os.path.exists(os.path.join(dest, "index.json")):
        return {"carried": False, "why": "the pack folder already has an attract/ (left alone)"}
    try:
        with open_release(url, size) as z:
            names = set(z.namelist())
            if ATTRACT not in names:
                return {"carried": False, "why": "the published pack has no attract/"}
            index = json.loads(z.read(ATTRACT))
            if not index.get("generated"):
                return {"carried": False, "why": "the published menu is hand-made (resorts/<slug>/attract/ makes it)"}
            if not (index.get("stills") or index.get("ghosts")):
                return {"carried": False, "why": "the published menu has no still or ghost takes"}
            files = attract_files(index)
            missing = [f for f in files if f"attract/{f}" not in names]
            if missing:
                raise OSError(f"the published attract/index.json lists files the zip lacks: {', '.join(missing)}")
            total = sum(z.getinfo(f"attract/{f}").file_size for f in files)
            if total > CARRY_MAX_BYTES:
                raise OSError(f"the published attract/ is {total / 1e6:.0f} MB, over {CARRY_MAX_BYTES / 1e6:.0f} MB")
            os.makedirs(pack_dir, exist_ok=True)
            tmp = tempfile.mkdtemp(prefix="attract-", dir=pack_dir)
            try:
                for f in files:
                    with open(os.path.join(tmp, f), "wb") as out:
                        out.write(z.read(f"attract/{f}"))
                os.makedirs(dest, exist_ok=True)     # all read: only now into the pack
                for f in files:
                    os.replace(os.path.join(tmp, f), os.path.join(dest, f))
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
    except (zipfile.BadZipFile, ValueError, KeyError) as e:
        raise OSError(f"{url}: {e}") from e
    stills, ghosts = list(index.get("stills") or []), list(index.get("ghosts") or [])
    log(f"  carried the published menu: {len(stills)} still(s), {len(ghosts)} ghost take(s), {total / 1e6:.1f} MB")
    return {"carried": True, "why": f"{len(stills)} still(s), {len(ghosts)} ghost take(s)", "stills": stills,
            "ghosts": ghosts, "bytes": total}

