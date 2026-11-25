"""Probe every data host a pack build calls (FEAT-245): one small request each, before the build job spends hours.

    python tools/ci/probe_hosts.py [--only NAME] [--timeout SECONDS] [--tuning host-tuning.json]
                                   [--raw-cache covered.json]

Each probe fetches one small item from a host the pipeline uses, with the URL the pipeline itself builds where it
can (constants imported from pipeline/, Vail's dataset and NAIP item for the per-resort ones), and checks what came
back (a TIFF, a WebP tile, JSON with the fields the pipeline reads, a 200 or 206 on a byte range of a big file).
FEAT-314: a probe that got no answer, a 429 or 5xx, or a bad body is retried inline by pipeline/retry.json's rules
(3 tries, waits 10 then 30 s, at most 300 s of waiting per run); a 4xx is not, unless retry.json lists it for the
host. --tuning (the metrics branch's host-tuning.json, build_failures.py) raises the timeout and tries of a host that
keeps timing out, within build_failures.CAP. The tries per host go to $SBA_RETRY_LOG (retry.Tally). Each row passes or
fails on its own (BUG-169: two rows on one host test two things, a route or a file each), except a host's mirrors
(Overpass, `mirror=True`): they pass when any mirror passes, tried in order, the next mirror only when the ones before
it failed (each gets its own row). web.archive.org is only for grooming (fetch_grooming.py), so it warns instead of
failing.

BUG-169: in a build-pack run (REBUILD or SLUG set, as build_pack_ci.py reads them) the row "NAIP items of <slug>"
asks Planetary Computer's STAC whether every NAIP item the slug's config (and the configs it builds on) names is still
in the catalog; items do leave it. A new resort has no config yet (resort.py plan picks current items), and a local
run names no slug: no row then.

BUG-170: rows marked plan_only are hosts only resort.py resolve and plan call, which run only for a new resort; on a
rebuild (the slug has a config) they only warn.
FEAT-347: --raw-cache names the file `raw_cache.py covered` writes when the raw-data cache covers every folder the
build reads, so the build fetches nothing: every host but its `keep` list then warns instead of failing.

Prints a table, appends it to $GITHUB_STEP_SUMMARY as Markdown when that is set, and exits 1 when a required host
failed. Uses curl (on ubuntu-latest and Windows 10+): Python's ssl rejects web.archive.org's chain (resort.py
curl_json).
"""
import argparse, json, os, re, subprocess, sys, tempfile, time
from dataclasses import dataclass
from typing import Callable
from urllib.parse import quote, urlencode, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
import gen_manifest  # noqa: E402
import paths  # noqa: E402
import placenames  # noqa: E402
import resort  # noqa: E402
import retry  # noqa: E402

UA = resort.UA
MAX_BODY = 64 * 1024           # bytes of the reply kept for the check
RANGE = "0-1023"               # big files (WorldCover, ETH canopy, GNIS, Census): the first KB only

# ---------------------------------------------------------------- checks: (http code, body bytes) -> (ok, detail)
# Pure, so the tests run them without the network.


def _json(body: bytes):
    try:
        return json.loads(body.decode("utf-8", "replace"))
    except ValueError:
        return None


def snippet(body: bytes, n: int = 80) -> str:
    return " ".join(body[:n].decode("utf-8", "replace").split())


def http_ok(code: int, body: bytes):
    return (code == 200, f"HTTP {code}")


def range_ok(code: int, body: bytes):
    """a byte range of a big file: 206 (or 200 from a server that ignores ranges) with something in it"""
    if code not in (200, 206):
        return False, f"HTTP {code}"
    return (len(body) > 0, f"HTTP {code}, {len(body)} bytes" if body else f"HTTP {code}, empty")


def json_with(*keys: str) -> Callable:
    """HTTP 200 and a JSON object holding every one of `keys`"""
    def check(code: int, body: bytes):
        if code != 200:
            return False, f"HTTP {code}: {snippet(body)}"
        d = _json(body)
        if not isinstance(d, dict):
            return False, f"not JSON: {snippet(body)}"
        missing = [k for k in keys if k not in d]
        if missing:
            return False, f"JSON without {', '.join(missing)}: {snippet(body)}"
        return True, f"HTTP 200, JSON with {', '.join(keys)}" if keys else "HTTP 200, JSON"
    return check


def any_json(code: int, body: bytes):
    """LFPS: any JSON reply, an error about the job id included, means the service is up; HTML means it is down
    (maintenance, fetch_landfire.mjs getJson). An unknown job id is HTTP 500 with {"message": "JobId not found.",
    "success": false}, so the code alone says nothing: the reply is JSON from the API, or it is not."""
    d = _json(body)
    if isinstance(d, dict) and ("success" in d or "message" in d):
        return True, f"HTTP {code}, LFPS JSON"
    if d is None or code >= 500:
        return False, f"HTTP {code}, not LFPS JSON: {snippet(body)}"
    return True, f"HTTP {code}, JSON"


def tiff(code: int, body: bytes):
    if code != 200:
        return False, f"HTTP {code}: {snippet(body)}"
    if body[:4] in (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+"):
        return True, f"HTTP 200, TIFF {len(body)} bytes"
    return False, f"not a TIFF: {snippet(body)}"


def webp(code: int, body: bytes):
    if code != 200:
        return False, f"HTTP {code}"
    if body[:4] == b"RIFF" and body[8:12] == b"WEBP":
        return True, f"HTTP 200, WebP {len(body)} bytes"
    return False, f"not a WebP: {snippet(body)}"


def overpass(code: int, body: bytes):
    """Overpass answers 200 with an HTML or remark body when it fails (fetch.ps1 checks the same two words)"""
    if code != 200:
        return False, f"HTTP {code}: {snippet(body)}"
    if b'"elements"' in body or b'"version"' in body:
        return True, "HTTP 200, Overpass JSON"
    return False, f"error body: {snippet(body)}"


def cdx(code: int, body: bytes):
    """the Internet Archive CDX API: a JSON list (header row first)"""
    if code != 200:
        return False, f"HTTP {code}: {snippet(body)}"
    return (isinstance(_json(body), list), "HTTP 200, CDX JSON" if isinstance(_json(body), list)
            else f"not JSON: {snippet(body)}")


# ---------------------------------------------------------------- the probes


@dataclass
class Probe:
    name: str                  # row name
    host: str                  # the host, as the summary and --tuning name it
    url: str
    check: Callable
    range: bool = False        # ask for the first KB only
    required: bool = True      # False: warn, do not fail
    mirror: bool = False       # one of the host's mirrors: the host passes when any of them passes
    plan_only: bool = False    # BUG-170: only resort.py resolve/plan calls it (a new resort): a rebuild only warns


def vail():
    """Vail's config: the per-resort probes (EPT dataset, NAIP item) use a resort every build of the pipeline has
    fetched"""
    with open(paths.config_path("vail"), encoding="utf-8") as f:
        return json.load(f)


def probes() -> list:
    cfg = vail()
    epsg = cfg["crs"].split(":")[1]
    x0, y0 = cfg["utm_bbox"][:2]
    # gen_manifest.py builds these inline (EXPORT, WC, ETH, the Overpass URLs); kept here in the same form. The NAIP
    # URL is gen_manifest.naip_url's own (BUG-169)
    export = ("https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/exportImage?" +
              urlencode({"bbox": f"{x0},{y0},{x0 + 16},{y0 + 16}", "bboxSR": epsg, "imageSR": epsg, "size": "16,16",
                         "format": "tiff", "pixelType": "F32", "noData": "-9999",
                         "interpolation": "RSP_BilinearInterpolation", "f": "image"}))
    # a 64 m corner of the first NAIP crop Vail's manifest fetches, 100 m in from its edge
    with open(os.path.join(paths.MANIFESTS, "vail.json"), encoding="utf-8") as f:
        first = next(it for it in json.load(f)["items"] if it["path"].startswith("naip1m/"))
    naip_item = first["meta"]["item"]
    cx, cy = first["meta"]["bbox"][0] + 100, first["meta"]["bbox"][1] + 100
    crop = gen_manifest.naip_url((cx, cy, cx + 64, cy + 64), 64, 64, naip_item, cfg["crs"])
    tile = "N39W108"           # the WorldCover / ETH 3 degree tile over Vail
    q = quote("[out:json][timeout:25];node(1);out;", safe="")
    box_ll = "-106.40,39.60,-106.39,39.61"
    tnm = "https://tnmaccess.nationalmap.gov/api/v1/products?" + urlencode(
        {"datasets": "Digital Elevation Model (DEM) 1 meter", "bbox": box_ll, "max": 1})
    cdx_url = "https://web.archive.org/cdx/search/cdx?" + urlencode(
        {"url": "vail.com", "output": "json", "filter": "statuscode:200", "limit": 1})
    rows = [
        Probe("3DEP ImageServer exportImage", "elevation.nationalmap.gov", export, tiff),
        Probe("TNM Access products", "tnmaccess.nationalmap.gov", tnm, json_with("items"), plan_only=True),
        Probe("3DEP work units (WESM.csv)", "prd-tnm.s3.amazonaws.com", resort.INDEXES["wesm.csv"], range_ok,
              range=True, plan_only=True),
        Probe("usgs-lidar-public EPT", "s3-us-west-2.amazonaws.com", cfg["lidar"]["ept"] + "ept.json",
              json_with("bounds", "schema")),
        Probe("Entwine boundaries", "usgs.entwine.io", resort.INDEXES["entwine_resources.geojson"], range_ok, range=True,
              plan_only=True),
        Probe("Planetary Computer STAC naip", "planetarycomputer.microsoft.com",
              "https://planetarycomputer.microsoft.com/api/stac/v1/collections/naip", json_with("id", "extent"),
              plan_only=True),
        Probe("Planetary Computer NAIP crop", "planetarycomputer.microsoft.com", crop, tiff),
        Probe("Mapterhorn tile", "tiles.mapterhorn.com", resort.MAPTERHORN_TILE.format(z=0, x=0, y=0), webp),
        Probe("Mapterhorn attribution", "download.mapterhorn.com", resort.INDEXES["mapterhorn_attribution.json"], http_ok,
              plan_only=True),
        Probe("Overpass", "Overpass", "https://overpass-api.de/api/interpreter?data=" + q, overpass, mirror=True),
        Probe("Overpass mirror private.coffee", "Overpass", "https://overpass.private.coffee/api/interpreter?data=" + q,
              overpass, mirror=True),
        Probe("Overpass mirror lz4", "Overpass", "https://lz4.overpass-api.de/api/interpreter?data=" + q, overpass,
              mirror=True),
        Probe("LANDFIRE LFPS", "lfps.usgs.gov", "https://lfps.usgs.gov/api/job/status?JobId=probe", any_json),
        Probe("ESA WorldCover", "esa-worldcover.s3.eu-central-1.amazonaws.com",
              f"https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_{tile}_Map.tif",
              range_ok, range=True),
        Probe("ETH canopy height", "libdrive.ethz.ch",
              "https://libdrive.ethz.ch/index.php/s/cO8or7iOe5dT2Rt/download?path=%2F3deg_cogs&files="
              f"ETH_GlobalCanopyHeight_10m_2020_{tile}_Map.tif", range_ok, range=True),
        Probe("USGS GNIS names", "prd-tnm.s3.amazonaws.com", placenames.GNIS_URL.format(st="CO"), range_ok, range=True),
        Probe("Census gazetteer", "www2.census.gov", placenames.GAZ_URL, range_ok, range=True),
        Probe("Census population", "www2.census.gov", placenames.POP_URL, range_ok, range=True),
        Probe("OpenSkiData ski areas", "tiles.openskimap.org", resort.INDEXES["ski_areas.geojson"], range_ok, range=True),
        Probe("Geofabrik index", "download.geofabrik.de", resort.INDEXES["geofabrik_index.json"], range_ok, range=True,
              plan_only=True),
        Probe("Internet Archive CDX (grooming)", "web.archive.org", cdx_url, cdx, required=False),
    ]
    built = build_naip_items()
    if built:
        slug, names = built
        # next to the NAIP route's row, so `--only NAIP` and `--only Planetary` both pick it
        at = next(k for k, p in enumerate(rows) if p.name == "Planetary Computer NAIP crop") + 1
        rows.insert(at, Probe(f"NAIP items of {slug}", "planetarycomputer.microsoft.com", stac_items_url(names),
                              naip_items_check(slug, names)))
    return rows


# ---------------------------------------------------------------- BUG-169: the NAIP items of the resort being built
STAC_SEARCH = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")      # build_pack_ci.SLUG_RE


def build_slug(env=None) -> str:
    """the slug a build-pack run builds, as build_pack_ci.check_inputs reads it: the rebuild list's pick, else the
    typed slug; "" in a local run or for anything that is not a slug (check_inputs refuses it)"""
    env = os.environ if env is None else env
    rebuild = (env.get("REBUILD") or "").strip()
    slug = rebuild if SLUG_RE.fullmatch(rebuild) else (env.get("SLUG") or "").strip()   # NEW is "(new resort: ...)"
    return slug if SLUG_RE.fullmatch(slug) and len(slug) <= 60 else ""


def naip_items(slug, resorts_dir=None, seen=None) -> list:
    """every NAIP item id the config of `slug` names, then those of the configs it builds on (`raw_from`, relocate
    sources: the build fetches their manifests too); [] when it has no config (a new resort)"""
    seen = set() if seen is None else seen
    if slug in seen:
        return []
    seen.add(slug)
    path = paths.config_path(slug, resorts_dir)
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    out = list((cfg.get("naip") or {}).get("item_bboxes_ll") or {})
    for dep in ([cfg["raw_from"]] if cfg.get("raw_from") else []) + \
            [m["source"] for m in cfg.get("relocate") or [] if m.get("source")]:
        out += [i for i in naip_items(dep, resorts_dir, seen) if i not in out]
    return out


def is_rebuild(env=None, resorts_dir=None) -> str:
    """BUG-170: the slug when this run rebuilds a resort that has a config (its committed config and manifest: no
    resolve or plan), else "" (a new resort, or a local run)"""
    slug = build_slug(env)
    return slug if slug and os.path.isfile(paths.config_path(slug, resorts_dir)) else ""


def build_naip_items(env=None, resorts_dir=None):
    """(slug, [item ids]) for the "NAIP items of <slug>" row, or None: no slug (a local run), no config yet (a new
    resort) or no NAIP (outside the US)"""
    slug = build_slug(env)
    names = naip_items(slug, resorts_dir) if slug else []
    return (slug, names) if names else None


def stac_items_url(names) -> str:
    return STAC_SEARCH + "?" + urlencode({"collections": "naip", "ids": ",".join(names), "limit": max(50, len(names))})


def naip_items_check(slug, names) -> Callable:
    """HTTP 200 and a STAC search reply holding every one of `names`"""
    def check(code: int, body: bytes):
        if code != 200:
            return False, f"HTTP {code}: {snippet(body)}"
        d = _json(body)
        if not isinstance(d, dict) or not isinstance(d.get("features"), list):
            return False, f"not a STAC search reply: {snippet(body)}"
        have = {f.get("id") for f in d["features"] if isinstance(f, dict)}
        gone = [n for n in names if n not in have]
        if gone:
            return False, (f"{len(gone)} of {len(names)} NAIP items are no longer in STAC: {', '.join(gone)}; "
                           f"python pipeline/resort.py plan {slug} picks current ones")
        return True, f"HTTP 200, all {len(names)} NAIP items in STAC"
    return check


# ---------------------------------------------------------------- running


def curl(url: str, timeout: int, byte_range: bool) -> tuple:
    """(http code, first MAX_BODY bytes, Retry-After seconds or None) by curl; code 0 when curl itself failed (DNS,
    TLS, timeout). %header{} needs curl 7.84; an older one prints it as is, which reads as no Retry-After"""
    fd, tmp = tempfile.mkstemp(prefix="probe-")
    os.close(fd)
    try:
        cmd = ["curl", "-sS", "-L", "-m", str(timeout), "-A", UA, "-o", tmp, "-w", "%{http_code}\n%header{retry-after}"]
        if byte_range:
            # a server that ignores the range would send the whole file (hundreds of MB): stop at 1 MB
            cmd += ["-r", RANGE, "--max-filesize", str(1 << 20)]
        p = subprocess.run(cmd + [url], capture_output=True, text=True)
        out = (p.stdout.strip().splitlines() or [""]) + [""]
        code = int(out[0]) if out[0].strip().isdigit() else 0
        after = int(out[1]) if out[1].strip().isdigit() else None
        with open(tmp, "rb") as f:
            body = f.read(MAX_BODY)
        if p.returncode and not code:
            return 0, (p.stderr.strip() or f"curl exited {p.returncode}").encode(), None
        if p.returncode == 63:   # --max-filesize: the server ignored the range, but it answered
            return code or 200, body or b"(range ignored)", None
        return code, body, after
    finally:
        os.remove(tmp)


def run_probe(p: Probe, fetch: Callable, tries: int = 0, budget: list | None = None) -> tuple:
    """(ok, detail, seconds, tries used) of one probe: retried while the answer is transient (retry.transient), up to
    `tries` times (retry.json's), and only while `budget` ([seconds of waiting left in this run]) lasts"""
    tries = tries or retry.RULES["probe"]["tries"]
    budget = budget if budget is not None else [retry.RULES["probe"]["budget_s"]]
    host = urlparse(p.url).hostname or ""
    t0 = time.time()
    k = 0
    while True:
        k += 1
        r = fetch(p.url, p.range)
        code, body, after = r[0], r[1], (r[2] if len(r) > 2 else None)
        ok, detail = p.check(code, body) if code else (False, snippet(body, 160))
        if ok or k >= tries:
            break
        if not retry.transient(code, host):
            detail += " (a 4xx: not retried)"
            break
        s = retry.wait("probe", k, after)
        if s > budget[0]:
            detail += " (retry budget used up)"
            break
        budget[0] -= s
        print(f"  retry {p.name} ({k}) in {s:.0f} s after: {detail}", flush=True)
        time.sleep(s)
    return ok, detail, time.time() - t0, k


def verdicts(results: list) -> dict:
    """{host: ok} of the hosts with mirrors, from [(probe, ok, detail, s)]: such a host passes when any mirror does.
    Every other row stands for itself (BUG-169: one row passing on a host says nothing of its other routes)"""
    out = {}
    for p, ok, _, _ in results:
        if p.mirror:
            out[p.host] = out.get(p.host, False) or bool(ok)
    return out


def failed_hosts(results: list) -> tuple:
    """(required hosts with a failed row, warn-only hosts with a failed row), a row of mirrors failing only when
    every mirror of its host did"""
    v = verdicts(results)
    bad, warn = set(), set()
    for p, ok, _, _ in results:
        if not (v[p.host] if p.mirror else ok):
            (bad if p.required else warn).add(p.host)
    return sorted(bad), sorted(warn - bad)


def status(p: Probe, ok, host_ok: bool) -> str:
    if ok is None:
        return "not tried (host ok)"
    if ok:
        return "ok"
    if host_ok:
        return "down (mirror ok)"
    return "FAIL" if p.required else "warn"


def table(results: list, markdown: bool = False) -> str:
    v = verdicts(results)
    rows = [(p.name, status(p, ok, p.mirror and v[p.host]), f"{s:.1f} s", detail) for p, ok, detail, s in results]
    if markdown:
        lines = ["| host | result | time | detail |", "|---|---|---|---|"]
        lines += ["| " + " | ".join(c.replace("|", "\\|") for c in r) + " |" for r in rows]
        return "\n".join(lines)
    w = [max(len(r[i]) for r in rows) for i in range(3)]
    return "\n".join(f"{r[0]:<{w[0]}}  {r[1]:<{w[1]}}  {r[2]:>{w[2]}}  {r[3]}" for r in rows)


def load_tuning(path) -> dict:
    """{host: {timeout, tries}} from build_failures.py's host-tuning.json, each value clamped to its cap"""
    if not path:
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return {h: {"timeout": max(1, min(180, int(t["timeout"]))), "tries": max(1, min(4, int(t["tries"])))}
                for h, t in d.items()}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return {}


def raw_cache_covers(path) -> tuple:
    """FEAT-347: (the folders the raw cache covers, the hosts still required) from `raw_cache.py covered`'s file;
    ([], set()) when there is none or it can't be read"""
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return [str(x) for x in d["covers"]], {str(x) for x in d["keep"]}
    except (OSError, ValueError, KeyError, TypeError):
        return [], set()


def main(argv=None, fetch: Callable | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--only", action="append", help="probe only rows or hosts whose name contains this (repeatable)")
    ap.add_argument("--timeout", type=int, default=60, help="seconds per request (default 60)")
    ap.add_argument("--tuning", help="JSON {host: {timeout, tries}}; a missing or bad file is ignored")  # FEAT-314
    ap.add_argument("--raw-cache", help="raw_cache.py covered's file; a missing or bad file is ignored")  # FEAT-347
    a = ap.parse_args(argv)
    tune = load_tuning(a.tuning)
    for h, t in tune.items():
        print(f"tuned: {h} {t['timeout']} s, {t['tries']} tries (build_failures.py host-tuning.json)")
    todo = probes()
    if a.only:
        keys = [o.lower() for o in a.only]
        todo = [p for p in todo if any(k in p.name.lower() or k in p.host.lower() for k in keys)]
        if not todo:
            print(f"no probe matches {a.only}")
            return 2
    rebuild = is_rebuild()
    planned = sorted({p.name for p in todo if rebuild and p.plan_only and p.required})
    for p in todo:
        if p.name in planned:
            p.required = False
    covers, keep = raw_cache_covers(a.raw_cache) if a.raw_cache else ([], set())
    downgraded = sorted({p.host for p in todo if covers and p.required and p.host not in keep})
    for p in todo:
        if p.host in downgraded:
            p.required = False
    cached = " ".join(
        ([f"A rebuild of {rebuild}: {', '.join(planned)} only warn, as only a new resort's plan calls them"
          "."] if planned else []) +
        ([f"Raw cache covers {', '.join(covers)}: {', '.join(downgraded)} only warn, as the build does not call "
          "them."] if downgraded else []))
    if cached:
        print(cached)
    results = []
    tally, budget = retry.Tally(), [retry.RULES["probe"]["budget_s"]]
    for p in todo:
        if p.mirror and verdicts(results).get(p.host):     # a mirror of a host that already answered: not needed
            results.append((p, None, "", 0.0))
            continue
        t = tune.get(p.host, {})
        f = fetch or (lambda url, rng, sec=t.get("timeout", a.timeout): curl(url, sec, rng))
        ok, detail, s, k = run_probe(p, f, tries=t.get("tries", 0), budget=budget)
        tally.add(urlparse(p.url).hostname or p.host, k, ok)
        results.append((p, ok, detail, s))
        print(f"{'ok  ' if ok else 'FAIL'} {p.name}: {detail}", flush=True)
    bad, warn = failed_hosts(results)
    why = ("not needed: the raw cache covers the build" if set(warn) & set(downgraded) else
           "only a new resort's plan calls them" if {p.host for p in todo if p.name in planned} & set(warn) else
           "grooming only")
    tally.save("probe")
    rec = sorted(h for h, t in tally.hosts.items() if t["recovered"])
    inline = (f"Recovered inline: {', '.join(rec)}. " if rec else "") + retry.caps_md()
    print("\n" + table(results) + "\n\n" + inline)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("### Data hosts\n\n" + table(results, markdown=True) + "\n\n" + inline + "\n\n")
            if cached:
                f.write(cached + "\n\n")
            if bad:
                f.write(f"**Unreachable:** {', '.join(bad)}. The build needs every one of them.\n\n")
            if warn:
                f.write(f"Warning: {', '.join(warn)} unreachable ({why}).\n\n")
    if warn:
        print(f"\nwarning: {', '.join(warn)} unreachable ({why})")
    if bad:
        print(f"\nunreachable: {', '.join(bad)}")
        return 1
    print(f"\nevery host answered ({len(results)} probes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
