"""How straight a pack's tree lines run (FEAT-378): the report `tree_lines.py` logs and keeps in meta
`treeLines.checks.straightness`, and prints with `python pipeline/tree_lines.py packs/<slug> --straightness [<run>]`."""
import math
import numpy as np

GRID = 2.0           # m: the ground's grid for the fall line and pitch
# the straightness report (FEAT-378, `straightness`)
SINUOSITY_W = (30.0, 90.0)   # m: stretches whose path over chord is measured
DRIFT_W = 60.0       # m: a stretch's most sideways stray off its chord
FALL_DEG = 15.0      # a step this close to the fall line counts as down it
PITCH_BANDS = (15.0, 25.0, 35.0)   # degrees
PITCH_SMOOTH = 8.0   # m: the ground's smoothing for the report's fall line and pitch
STRAIGHT_TOL = 1.5   # m: a stretch never further than this off its chord runs straight (a gentle wiggle included)
TREES_D = 12.0       # m: a point this close to a detected trunk is in the trees
NEAR_M = 150.0       # m: --straightness keeps the lines this close to the run


def off_chord(q):
    """the most the points `q` (n, 2) stray from the chord from the first to the last, m"""
    d = q[-1] - q[0]
    L = math.hypot(d[0], d[1])
    if L < 1e-6:
        return float(np.hypot(*(q - q[0]).T).max())
    return float(np.abs((q[:, 0] - q[0, 0]) * d[1] - (q[:, 1] - q[0, 1]) * d[0]).max() / L)


def straightness(lines, hts, near=None, trunks=None):
    """FEAT-378: how straight the lines run. Path over chord on every SINUOSITY_W m stretch (1 is a ruler), the most a
    DRIFT_W m stretch strays from its chord (m), and the share of the line within FALL_DEG of the fall line by pitch band
    (PITCH_BANDS, degrees; the ground smoothed over PITCH_SMOOTH m). Medians and p90s over all stretches of all lines;
    `near` (runs' points) keeps the lines with a point within NEAR_M m of one. With `trunks` (a cKDTree of the detected
    trunks), each line's longest straight stretch in the trees (never more than STRAIGHT_TOL m off its chord, every
    point within TREES_D m of a trunk) by the stretch's pitch band: median and p90 over the lines."""
    from scipy import ndimage
    from scipy.spatial import cKDTree
    from pack_report import resample
    sin = {w: [] for w in SINUOSITY_W}
    drift, kept = [], 0
    bands = np.zeros((len(PITCH_BANDS) + 1, 2))
    longest = [[] for _ in range(len(PITCH_BANDS) + 1)]
    kd = cKDTree(np.concatenate([resample(np.asarray(q, np.float64)[:, :2], 5.0) for q in near])) if near else None
    for ln in lines:
        p = np.asarray(ln["p"], np.float64).reshape(-1, 4)[:, :2]
        if len(p) < 3 or (kd is not None and not np.isfinite(kd.query(p, distance_upper_bound=NEAR_M)[0]).any()):
            continue
        kept += 1
        s = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(p, axis=0).T))])
        for w in SINUOSITY_W:
            j = np.searchsorted(s, s + w)
            i = np.nonzero(j < len(s))[0]
            ch = np.hypot(*(p[j[i]] - p[i]).T)
            sin[w] += list((s[j[i]] - s[i]) / np.maximum(ch, 1e-6))
        j = np.searchsorted(s, s + DRIFT_W)
        for i in np.nonzero(j < len(s))[0]:
            a, b = p[i], p[j[i]]
            d = b - a; n = np.array([-d[1], d[0]]) / max(np.hypot(*d), 1e-6)
            drift.append(float(np.abs((p[i:j[i] + 1] - a) @ n).max()))
        x0, y1 = p[:, 0].min() - 12, p[:, 1].max() + 12
        w, h = int(math.ceil((p[:, 0].max() + 12 - x0) / GRID)), int(math.ceil((y1 - p[:, 1].min() + 12) / GRID))
        z = hts.window(x0, y1, w, h, GRID)
        if not np.isfinite(z).any():
            continue
        zs = ndimage.gaussian_filter(np.where(np.isfinite(z), z, np.nanmean(z)).astype(np.float64), PITCH_SMOOTH / GRID, mode="nearest")
        gr, gc = np.gradient(zs, GRID)
        m = 0.5 * (p[:-1] + p[1:]); d = np.diff(p, axis=0); L = np.hypot(*d.T)
        c = np.clip(((m[:, 0] - x0) / GRID).astype(int), 0, w - 1); r = np.clip(((y1 - m[:, 1]) / GRID).astype(int), 0, h - 1)
        fx, fy = -gc[r, c], gr[r, c]   # downhill, x east / y north
        g = np.hypot(fx, fy)
        cos = (d[:, 0] * fx + d[:, 1] * fy) / np.maximum(L * g, 1e-9)
        pitch = np.degrees(np.arctan(g))
        band = np.searchsorted(PITCH_BANDS, pitch)
        on = cos >= math.cos(math.radians(FALL_DEG))
        np.add.at(bands, (band, 0), L * on); np.add.at(bands, (band, 1), L)
        if trunks is not None:
            # greedy maximal straight stretches over the segments in the trees, each the band of its mean pitch
            ok = np.isfinite(trunks.query(p, distance_upper_bound=TREES_D)[0])
            best = np.zeros(len(PITCH_BANDS) + 1)
            i = 0
            while i < len(p) - 1:
                if not (ok[i] and ok[i + 1]):
                    i += 1; continue
                j = i + 1
                while j + 1 < len(p) and ok[j + 1] and off_chord(p[i:j + 2]) <= STRAIGHT_TOL:
                    j += 1
                b = int(np.searchsorted(PITCH_BANDS, pitch[i:j].mean()))
                best[b] = max(best[b], s[j] - s[i])
                i = j
            for b in range(len(best)):
                if best[b] > 0:
                    longest[b].append(best[b])
    q = lambda v: {"median": round(float(np.median(v)), 3), "p90": round(float(np.percentile(v, 90)), 3)} if len(v) else None
    edges = [0, *PITCH_BANDS, 90]
    return {"lines": kept, **{f"sinuosity{w:g}": q(sin[w]) for w in SINUOSITY_W}, f"drift{DRIFT_W:g}": q(drift),
            "fallLine": {f"{edges[k]:g}-{edges[k + 1]:g}": (round(float(bands[k, 0] / bands[k, 1]), 3) if bands[k, 1] > 0 else None)
                         for k in range(len(edges) - 1)},
            "km": {f"{edges[k]:g}-{edges[k + 1]:g}": round(float(bands[k, 1] / 1000), 2) for k in range(len(edges) - 1)},
            **({"straightInTrees": {f"{edges[k]:g}-{edges[k + 1]:g}": q(longest[k]) for k in range(len(edges) - 1)}}
               if trunks is not None else {})}
