"""FEAT-346: what each raw file was fetched for, so a file is reused while it still fits and fetched again once it
doesn't.

fetch.ps1 skips a file that is already on disk, by its path alone. That keeps a file the manifest now wants made
differently (a new bbox, size or query under the same name), and it is what lets a restored raw folder
(tools/ci/raw_cache.py) skip everything. This module gives each manifest item a key for what its bytes are:

    sha(path, meta)  when the item has `meta` (DEM, NAIP, land cover: bbox, size, res, item), so a new URL for the
                     same bytes (a host's route renamed) keeps the file
    sha(path, url)   otherwise (EPT nodes, Mapterhorn tiles, OSM queries, names): the URL is what was asked for

A change in how a meta source's bytes are made (its resampling, say) goes in that item's `meta`, so its key changes.

    prune(raw, items)   before the fetch: delete each file whose recorded key differs from the manifest's
    record(raw, items)  after a fetch that finished: write <raw>/fetch_index.json, {path: key}

A raw folder from before FEAT-346 has no index: nothing is pruned (its files are trusted, as before), and the next
finished fetch records them."""
import hashlib
import json
import os

INDEX = "fetch_index.json"


def item_key(item: dict) -> str:
    what = item["meta"] if "meta" in item else item["url"]
    return hashlib.sha256(json.dumps([item["path"], what], sort_keys=True).encode()).hexdigest()[:16]


def _file(raw: str, path: str) -> str:
    """<raw>/<path> on this platform; a manifest path that would leave the raw folder raises"""
    full = os.path.normpath(os.path.join(raw, *path.split("/")))
    if os.path.commonpath([os.path.abspath(raw), os.path.abspath(full)]) != os.path.abspath(raw):
        raise ValueError(f"manifest path {path!r} is outside the raw folder")
    return full


def load(raw: str) -> dict:
    try:
        with open(os.path.join(raw, INDEX), encoding="utf-8") as f:
            index = json.load(f)
        return index if isinstance(index, dict) else {}
    except (OSError, ValueError):
        return {}


def prune(raw: str, items: list[dict]) -> list[str]:
    """delete the files whose recorded key is not the manifest's any more; -> their paths"""
    index, gone = load(raw), []
    for item in items:
        path = item["path"]
        was = index.get(path)
        if was is None or was == item_key(item):
            continue
        full = _file(raw, path)
        if os.path.isfile(full):
            os.remove(full)
            gone.append(path)
    return gone


def record(raw: str, items: list[dict]) -> None:
    index = {item["path"]: item_key(item) for item in items}
    tmp = os.path.join(raw, INDEX + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(index, f, indent=0, sort_keys=True)
        f.write("\n")
    os.replace(tmp, os.path.join(raw, INDEX))
