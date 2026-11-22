"""FEAT-346: what each raw file was fetched for, and (FEAT-348) when, so a file is reused while it still fits and
fetched again once it doesn't or once it is too old.

fetch.ps1 skips a file that is already on disk, by its path alone. That keeps a file the manifest now wants made
differently (a new bbox, size or query under the same name), and it is what lets a restored raw folder
(tools/ci/raw_cache.py) skip everything. This module gives each manifest item a key for what its bytes are:

    sha(path, meta)  when the item has `meta` (DEM, NAIP, land cover: bbox, size, res, item), so a new URL for the
                     same bytes (a host's route renamed) keeps the file
    sha(path, url)   otherwise (EPT nodes, Mapterhorn tiles, OSM queries, names): the URL is what was asked for

A change in how a meta source's bytes are made (its resampling, say) goes in that item's `meta`, so its key changes.

FEAT-348: some layers go stale on their own. MAX_AGE_DAYS gives a maximum age by path prefix (OpenStreetMap, 14
days: the layer that changes most, and about 8 MB and 5 Overpass requests per resort); an item older than that is
fetched again as if its key had changed. The other layers (DEM, NAIP, lidar, Mapterhorn, land cover, names) have no
maximum age.

    over_age(raw, items, now)          the items whose fetch time is past their maximum age
    prune(raw, items, now)             before the fetch: delete each file whose key changed or that is over age
    record(raw, items, fetched, now)   after a fetch that finished: write <raw>/fetch_index.json,
                                       {path: {"key", "fetched"}}; `fetched` names the files this fetch downloaded,
                                       which get `now`, and every other item keeps the time it has

record keeps the times it finds, so recording a folder that downloaded nothing writes the same bytes (the raw
cache's key hashes this file: a rebuild from a restored cache must not upload it again).

A raw folder from before FEAT-346 has no index: nothing is pruned (its files are trusted, as before), and the next
record writes them. An index from before FEAT-348 ({path: key}) is read with no fetch times: an unknown time is
never over age and is recorded as now, so the upgrade deletes nothing and the 14 days start then (that form was
only ever written by FEAT-346 builds a few days before this card)."""
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone

INDEX = "fetch_index.json"
MAX_AGE_DAYS = {"osm/": 14}


def item_key(item: dict) -> str:
    what = item["meta"] if "meta" in item else item["url"]
    return hashlib.sha256(json.dumps([item["path"], what], sort_keys=True).encode()).hexdigest()[:16]


def max_age(path: str) -> int | None:
    """the item's maximum age in days, None for none"""
    return next((d for prefix, d in MAX_AGE_DAYS.items() if path.startswith(prefix)), None)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def stamp(t: datetime) -> str:
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _file(raw: str, path: str) -> str:
    """<raw>/<path> on this platform; a manifest path that would leave the raw folder raises"""
    full = os.path.normpath(os.path.join(raw, *path.split("/")))
    if os.path.commonpath([os.path.abspath(raw), os.path.abspath(full)]) != os.path.abspath(raw):
        raise ValueError(f"manifest path {path!r} is outside the raw folder")
    return full


def load(raw: str) -> dict:
    """{path: {"key", "fetched"}}; an entry in the old {path: key} form has "fetched": None"""
    try:
        with open(os.path.join(raw, INDEX), encoding="utf-8") as f:
            index = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(index, dict):
        return {}
    out = {}
    for path, e in index.items():
        if isinstance(e, str):
            out[path] = {"key": e, "fetched": None}
        elif isinstance(e, dict) and isinstance(e.get("key"), str):
            out[path] = {"key": e["key"], "fetched": e.get("fetched") if isinstance(e.get("fetched"), str) else None}
    return out


def _fetched_at(entry: dict) -> datetime | None:
    try:
        return datetime.strptime(entry["fetched"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def over_age(raw: str, items: list[dict], now: datetime | None = None, index: dict | None = None) -> list[str]:
    """the paths whose recorded fetch is older than their maximum age (an item whose key changed is not counted:
    it goes again for that)"""
    now, index = now or utc_now(), load(raw) if index is None else index
    out = []
    for item in items:
        days, e = max_age(item["path"]), index.get(item["path"])
        if days is None or e is None or e["key"] != item_key(item):
            continue
        t = _fetched_at(e)
        if t is not None and now - t > timedelta(days=days):
            out.append(item["path"])
    return out


def prune(raw: str, items: list[dict], now: datetime | None = None) -> list[str]:
    """delete the files whose recorded key is not the manifest's any more, or that are over age; -> their paths"""
    index = load(raw)
    stale = set(over_age(raw, items, now, index))
    gone = []
    for item in items:
        path = item["path"]
        e = index.get(path)
        if e is None or (e["key"] == item_key(item) and path not in stale):
            continue
        full = _file(raw, path)
        if os.path.isfile(full):
            os.remove(full)
            gone.append(path)
    return gone


def missing(raw: str, items: list[dict]) -> list[str]:
    """the paths not on disk: what the next fetch downloads"""
    return [item["path"] for item in items if not os.path.isfile(_file(raw, item["path"]))]


def record(raw: str, items: list[dict], fetched=(), now: datetime | None = None) -> None:
    old, fetched, when = load(raw), set(fetched), stamp(now or utc_now())
    index = {}
    for item in items:
        e = old.get(item["path"])
        keep = e is not None and e["fetched"] and item["path"] not in fetched
        index[item["path"]] = {"key": item_key(item), "fetched": e["fetched"] if keep else when}
    text = json.dumps(index, indent=0, sort_keys=True) + "\n"
    path = os.path.join(raw, INDEX)
    try:
        with open(path, encoding="utf-8", newline="") as f:
            if f.read() == text:
                return                        # unchanged: the same bytes, and the file is not touched
    except OSError:
        pass
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(tmp, path)
