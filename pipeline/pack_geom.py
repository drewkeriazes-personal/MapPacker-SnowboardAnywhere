"""Geometry helpers for the tree lines (FEAT-334, FEAT-378): the pack's fine heights read a window at a time, a run's
centreline, a smoothstep, a stable hash, a point's distance to a segment. tree_lines.py re-exports them."""
import math
import os
import numpy as np
from PIL import Image


def smooth(e0, e1, v):
    t = np.clip((np.asarray(v, np.float64) - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def h01(*k):
    """a stable hash of integers to 0..1"""
    h = 2166136261
    for v in k:
        for b in int(v).to_bytes(8, "little", signed=True):
            h = ((h ^ b) * 16777619) & 0xFFFFFFFF
    h ^= h >> 13; h = (h * 1274126177) & 0xFFFFFFFF; h ^= h >> 16
    return (h & 0xFFFFFF) / 0x1000000


class Heights:
    """the fine height set, read a tile at a time"""
    def __init__(self, pack_dir, meta):
        from packwriter import decode_terrarium
        self.dec = decode_terrarium
        t = meta["terrain"]
        self.m = t.get("fine") or t["coarse"]
        self.dir = os.path.join(pack_dir, "fine" if t.get("fine") else "coarse")
        self.cache = {}

    def tile(self, tx, ty):
        k = (tx, ty)
        if k not in self.cache:
            p = os.path.join(self.dir, f"{tx}_{ty}.png")
            T = self.m["tileSize"]
            self.cache[k] = self.dec(np.asarray(Image.open(p).convert("RGB"))) if os.path.exists(p) else np.full((T, T), np.nan, np.float32)
        return self.cache[k]

    def window(self, x0, y1, w, h, res):
        """heights at cell centres of a w x h grid of `res` m cells from (x0, y1) (its north-west corner), row 0 = north"""
        m, T = self.m, self.m["tileSize"]
        r = m["res"]
        xs = x0 + (np.arange(w) + 0.5) * res
        ys = y1 - (np.arange(h) + 0.5) * res
        out = np.full((h, w), np.nan, np.float32)
        # the nearest fine sample of each sub-cell, averaged over the cell (k x k sub-samples)
        k = max(1, int(round(res / r)))
        acc = np.zeros((h, w), np.float64); cnt = np.zeros((h, w), np.float64)
        for a in range(k):
            for b in range(k):
                sx = xs - res / 2 + (a + 0.5) * res / k
                sy = ys - res / 2 + (b + 0.5) * res / k
                gc = np.floor((sx - m["minX"]) / r).astype(np.int64)
                gr = np.floor((sy - m["minY"]) / r).astype(np.int64)   # from the south
                txs, tys = gc // T, gr // T
                for ty in np.unique(tys):
                    for tx in np.unique(txs):
                        if tx < 0 or ty < 0 or tx >= m["tilesX"] or ty >= m["tilesY"]:
                            continue
                        cj = np.nonzero(txs == tx)[0]; ri = np.nonzero(tys == ty)[0]
                        tile = self.tile(int(tx), int(ty))
                        v = tile[np.ix_(T - 1 - (gr[ri] - ty * T), gc[cj] - tx * T)]
                        ok = np.isfinite(v)
                        sub = acc[np.ix_(ri, cj)]; sub[ok] += v[ok]; acc[np.ix_(ri, cj)] = sub
                        sc = cnt[np.ix_(ri, cj)]; sc[ok] += 1; cnt[np.ix_(ri, cj)] = sc
        good = cnt > 0
        out[good] = (acc[good] / cnt[good]).astype(np.float32)
        return out


def run_line(r):
    """a run's centreline downhill first, with its arc length, or None"""
    p = np.asarray(r["points"], np.float64)
    if len(p) < 2:
        return None
    if p[0, 2] < p[-1, 2]:
        p = p[::-1]
    s = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(p[:, 0]), np.diff(p[:, 1])))])
    return (p, s) if s[-1] > 20 else None


def along(p, s, q):
    """point and unit tangent at arc length q"""
    q = min(max(q, 0.0), s[-1])
    i = min(int(np.searchsorted(s, q, side="right")) - 1, len(s) - 2)
    i = max(i, 0)
    sl = max(s[i + 1] - s[i], 1e-9); t = (q - s[i]) / sl
    a, b = p[i], p[i + 1]
    return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, (b[0] - a[0]) / sl, (b[1] - a[1]) / sl


def seg_dist(pt, a, b):
    d = b - a; l2 = float(d @ d)
    t = 0.0 if l2 <= 0 else min(1.0, max(0.0, float((pt - a) @ d) / l2))
    e = a + d * t - pt
    return math.hypot(e[0], e[1])
