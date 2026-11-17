#!/usr/bin/env python3
"""Canopy density grid (FEAT-331): how thick and tall the tree canopy is round each spot, for the game's glade
darkness (SnowboardAnywhere FEAT-330).

python pipeline/canopy.py packs/<slug> [--at x,y ...]

Writes canopy.png at the pack root (8-bit greyscale, row 0 = north, pixel / 255 = score 0..1, RES m cells over the
pack bounds) and the `canopy` entry of meta.json. Runs standalone on a built pack (no raw data, no rebuild) and from
build_pack.py after the cover levels. --at prints the score at local points (metres, the meta.json frame).

Score per cell, from the trees the game draws taller than MIN_H:
  v = sum(crown area x height) / cell area        (m: the drawn crown cover times its mean height)
the detected crowns (trees/*.bin, at the radius the game draws them) plus the stand's generated stems in expectation
(stands/, chance x crown area; a stem counts by the share of its 0.75..1 x stand height draw over MIN_H), blurred
over BLUR_M and mapped linearly from V_OPEN (0) to V_CLOSED (1), clamped. The references are fixed physical
amounts, not the pack's own maximum, so the same score means the same forest in every pack:
  V_CLOSED  6 m: 40% of the ground under the crowns of 15 m trees, a dense glade you can still ride between (Vail's
            timber draws 0.4 to 0.75 cover at 18 to 25 m, 7 to 19 m, so it saturates; Steep and Deep reads about 1)
  V_OPEN    1.5 m: 10% of the ground under 15 m crowns (about where WorldCover starts calling a pixel tree cover),
            the scattered trees of a bowl or a run's edge, reads as open
"""
import json, math, os, sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

RES = 10.0          # m per cell
MIN_H = 10.0        # m: shorter trees (krummholz, young stands, the snow ghosts at the treeline) make no room overhead
V_OPEN = 1.5        # m of crown cover x height that still reads as open terrain (score 0): 0.1 cover at 15 m
V_CLOSED = 6.0      # m that reads as a closed room of tall trees (score 1): 0.4 cover at 15 m
BLUR_M = 15.0       # Gaussian sigma (m) over the cells, so a glade's edge fades over 20 to 30 m
FILE = "canopy.png"
STEM_LO = 0.75      # the game draws a generated stem 0.75..1 x the stand height (stands.STEM_H is the mean)


def grid(meta, res=RES):
    """the grid over the pack bounds: (minX, minY, w, h); row 0 is the top edge, minY + h * res"""
    b = meta["bounds"]
    w = int(math.ceil((b["maxX"] - b["minX"]) / res - 1e-9))
    h = int(math.ceil((b["maxY"] - b["minY"]) / res - 1e-9))
    return float(b["minX"]), float(b["minY"]), w, h


def _cells(x, y, min_x, top, res, w, h):
    c = np.floor((np.asarray(x, np.float64) - min_x) / res).astype(np.int64)
    r = np.floor((top - np.asarray(y, np.float64)) / res).astype(np.int64)
    return c, r, (c >= 0) & (c < w) & (r >= 0) & (r < h)


def canopy_volume(pack_dir, meta, res=RES, min_h=MIN_H):
    """sum of drawn crown area x height per cell over the cell area (m), row 0 = north, over grid(meta, res)"""
    import cover, stands
    min_x, min_y, w, h = grid(meta, res)
    top = min_y + h * res
    v = np.zeros((h, w), np.float64)
    wide = cover.drawn(meta)
    for t in cover.tree_records(pack_dir, meta):
        tall = t[:, 3] > min_h
        t = t[tall]
        cr = cover.crown_radii(t[:, 5], t[:, 3], t[:, 4], wide)
        c, r, ok = _cells(t[:, 0], t[:, 1], min_x, top, res, w, h)
        np.add.at(v, (r[ok], c[ok]), (np.pi * cr ** 2 * t[:, 3])[ok])
    st, inst = meta.get("stands"), meta.get("instances") or {}
    if st:
        import widths
        cw = inst.get("crownWidths")
        for cx, cy, p, hh, sp, _z, wf in stands.read_all(pack_dir, meta, with_width=True):
            i, j = np.nonzero(p > 0)
            H = hh[i, j].astype(np.float64)
            # the share of the stem's height draw (uniform STEM_LO..1 x H) over min_h, and its mean height there
            lo = np.maximum(STEM_LO * H, min_h)
            share = np.clip((H - lo) / np.maximum((1 - STEM_LO) * H, 1e-6), 0, 1)
            keep = share > 0
            if not keep.any():
                continue
            i, j, H, lo, share = i[keep], j[keep], H[keep], lo[keep], share[keep]
            hm = (lo + H) / 2
            spp = np.clip(sp[i, j], 0, len(stands.CROWN_RATIO) - 1).astype(np.int64)
            a = p[i, j] * share * np.pi * (stands.CROWN_RATIO[spp] * hm) ** 2
            if cw:   # FEAT-298: the stems' widths, their own draw in expectation
                a = a * widths.area_factor(spp, wf[i, j])
            x = inst["minX"] + cx * inst["cellSize"] + (j + 0.5) * st["res"]
            y = inst["minY"] + (cy + 1) * inst["cellSize"] - (i + 0.5) * st["res"]
            c, r, ok = _cells(x, y, min_x, top, res, w, h)
            np.add.at(v, (r[ok], c[ok]), (a * hm)[ok])
    return (v / (res * res)).astype(np.float32)


def score(vol, res=RES):
    """the 0..1 canopy score from canopy_volume: blurred over BLUR_M, then V_OPEN..V_CLOSED mapped to 0..1"""
    from scipy import ndimage
    v = ndimage.gaussian_filter(vol.astype(np.float32), BLUR_M / res, mode="nearest")
    return np.clip((v - V_OPEN) / (V_CLOSED - V_OPEN), 0, 1).astype(np.float32)


def build_canopy(pack_dir, meta, log=print):
    """write canopy.png and return the meta entry"""
    min_x, min_y, w, h = grid(meta)
    s = score(canopy_volume(pack_dir, meta))
    px = np.round(s * 255).astype(np.uint8)
    path = os.path.join(pack_dir, FILE)
    Image.fromarray(px, "L").save(path, optimize=True)
    log(f"  canopy {w} x {h} at {RES:g} m: mean {s.mean():.3f}, {(s >= 0.5).mean() * 100:.1f}% at 0.5 or more, "
        f"{(s >= 0.95).mean() * 100:.1f}% closed; {os.path.getsize(path) / 1e3:.0f} KB")
    return {"res": RES, "minX": min_x, "minY": min_y, "w": w, "h": h, "file": FILE}


def read(pack_dir, meta):
    """the pack's canopy score (h, w) float 0..1 and its meta entry, or (None, None) without one"""
    e = meta.get("canopy")
    if not e:
        return None, None
    return np.asarray(Image.open(os.path.join(pack_dir, e["file"])), np.float32) / 255.0, e


def sample(img, entry, x, y):
    """bilinear score at local (x, y) between cell centres, as a reader of the grid would (0 off the grid)"""
    res, w, h = entry["res"], entry["w"], entry["h"]
    fx = (x - entry["minX"]) / res - 0.5
    fy = (entry["minY"] + h * res - y) / res - 0.5
    if fx < -0.5 or fy < -0.5 or fx > w - 0.5 or fy > h - 0.5:
        return 0.0
    fx, fy = min(max(fx, 0), w - 1), min(max(fy, 0), h - 1)
    x0, y0 = int(fx), int(fy)
    x1, y1 = min(x0 + 1, w - 1), min(y0 + 1, h - 1)
    tx, ty = fx - x0, fy - y0
    top = img[y0, x0] + (img[y0, x1] - img[y0, x0]) * tx
    bot = img[y1, x0] + (img[y1, x1] - img[y1, x0]) * tx
    return float(top + (bot - top) * ty)


def main(argv):
    if not argv or argv[0].startswith("-"):
        sys.exit(__doc__)
    pack_dir, at = argv[0], []
    if "--at" in argv:
        at = [tuple(float(v) for v in a.split(",")) for a in argv[argv.index("--at") + 1:]]
    mp = os.path.join(pack_dir, "meta.json")
    meta = json.load(open(mp, encoding="utf-8"))
    meta["canopy"] = build_canopy(pack_dir, meta)
    from packwriter import stamp_build
    stamp_build(meta)   # FEAT-177: the pack changed, so it is a new build (the game's get --from copies it again)
    with open(mp, "w") as f:
        json.dump(meta, f, indent=1)
    img, e = read(pack_dir, meta)
    for x, y in at:
        print(f"  ({x:.0f}, {y:.0f}): {sample(img, e, x, y):.2f}")


if __name__ == "__main__":
    main(sys.argv[1:])
