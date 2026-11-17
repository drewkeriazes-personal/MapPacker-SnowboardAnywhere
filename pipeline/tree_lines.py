#!/usr/bin/env python3
"""Glade tree lines from the terrain (FEAT-334): the worn lines riders cut down through the trees beside the black and
gladed runs, traced on a cost field over the pack's own ground and trunks, for the game's trenches, moguls and trim
(SnowboardAnywhere FEAT-333, game/src/pack/treeLines.ts).

python pipeline/tree_lines.py packs/<slug> [--only <run name>]

Writes treeLines.json at the pack root and the `treeLines` entry of meta.json. Runs standalone on a built pack (no raw
data, no rebuild) and from build_pack.py after the canopy grid. --only plans the runs whose name holds the text (a
quick look at one glade; the pack it writes then holds only those lines).

Per run that gets lines (gladed, or advanced / expert / freeride / extreme), on a RES m grid over the run's box plus PAD:
  1. Terrain. The fine set's heights (1 m, averaged to RES), smoothed over SMOOTH m for the fall line.
  2. Obstacles. The pack's detected trunks (trees/*.bin) as a distance-to-trunk raster. Closer than BLOCK m is
     impassable (a full corridor's half-width plus the trench wall the game keeps clear, squeezed); out to CLEAR m it
     costs more.
  3. Cost field. Each move between neighbouring cells costs its length times (1 + ANGLE_K (1 - cos) of the angle off the
     fall line, on ground steep enough to have one) times (1 + FLAT_K where the move drops less than STALL_TAN, a rider
     bogging down) times the trunk penalty, plus RISE_K per m it climbs (the smoothed ground has pits; no fill). The
     runs' own corridors are walls (lines stay in the trees, a gladed run is trees) except the exits: the run's last
     FOOT_M m (so the lines funnel to it where the run flattens out) and any run lower than its foot. One backward Dijkstra from the exits gives each cell its cost to get out.
  4. Riders. Seeds every SEED_GAP m (Poisson disk, SEED_GAP_TREES beside a tree run) in a band OFF_MIN..OFF_MAX m off
     the run on both sides, over its upper SEED_SPAN, plus ENTRY_LINES entrances across a tree run's top edge (ENTRY_OFF + ENTRY_DOFF i m out). Highest first,
     each rider walks down the field (the cheapest next step, with a little noise of its own) until it gets out, stalls
     or meets a line already ridden (within JOIN cells): then it joins it, and that line carries one more rider from
     there down. So lines merge in gullies and funnel at flats by themselves, and the busy ones are the deep ones.
  5. Smooth. Resampled every STEP m, smoothed with the ends held, curvature clamped to R_MIN, then the corridor checked
     against the trunks: squeezed to SQUEEZE_HW past one closer than its rim, broken for a step (ramped over RAMP_STEPS)
     where even that hits. Stretches more than OPEN_D m from any trunk are left out (no forest, nothing to wear; the
     game gates by its cover levels too). Each point carries its half-width and strength (riders: STR_LO at one rider
     up to 1 at STR_RIDERS or more), fading in at a seed and out at an exit.
  6. Validate. No trunk inside a corridor; stall stretches (flatter than STALL_TAN for over STALL_M m) counted; the
     spacing between neighbouring lines in the glades. Logged, and kept in meta `treeLines.checks`.
Pure: the same pack gives the same lines.

treeLines.json: {"version": 1, "step": STEP, "lines": [{"p": [x, y, half-width, strength, ...], "open": m}, ...]}, pack
metres (x east, y north); `open` (optional) is how many metres from a line's start the game's forest gate does not
apply (an entrance leaving the cat track).
"""
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

FILE = "treeLines.json"
VERSION = 1
LINE_DIFF = {"advanced", "expert", "freeride", "extreme"}
TREE_RUN = {"expert", "freeride", "extreme"}
RES = 2.0            # m: the cost field's grid
PAD = 160.0          # m round a run's box
SMOOTH = 3.0         # m: Gaussian sigma for the fall line
ANGLE_K = 3.0        # cost per unit (1 - cos) off the fall line
ANGLE_LO, ANGLE_HI = 0.05, 0.2   # slope (tan) over which the fall line starts to matter
STALL_TAN = math.tan(math.radians(9))   # flatter than this a rider bogs down
FLAT_K = 2.0
RISE_K = 25.0        # cost per m climbed
BLOCK = 1.7          # m: a trunk closer than this to a cell blocks it (SQUEEZE_HW + TRENCH_WALL, plus a little)
CLEAR = 4.0          # m: a trunk within this costs more
TREE_K = 2.5
FOOT_M = 80.0        # m: the run's last stretch, where its lines get out
RUN_KEEP = {"novice": 13, "easy": 12, "intermediate": 11, "advanced": 9, "expert": 8, "freeride": 8, "extreme": 8}
SEED_GAP, SEED_GAP_TREES = 45.0, 28.0
OFF_MIN, OFF_MAX = 12.0, 130.0
SEED_SPAN = 0.85     # share of the run's length (from its top) that gets seeds
SEEDS_MAX = 60
ENTRY_LINES, ENTRY_S0, ENTRY_DS, ENTRY_OFF, ENTRY_DOFF, ENTRY_OPEN = 3, 4.0, 10.0, 12.0, 8.0, 70.0
EDGE_M, EDGE_K = 6.0, 0.6   # m: a cell this close to a run's corridor costs up to 1 + EDGE_K (lines keep off its edge)
NOISE = 0.25         # a rider's noise on each step's cost, times the step's length
JOIN = 1             # cells: a rider this close to a ridden line joins it, on a steep pitch
JOIN_FLAT = 4        # cells: on the flats (under STALL_TAN, from JOIN at FUNNEL_TAN): nobody breaks trail where they bog down
FUNNEL_TAN = 0.36
MAX_STEPS = 2500
MIN_LEN = 30.0       # m: a shorter line is left out (its rider still counts on the line it joined)
STEP = 3.0           # m between exported points
SMOOTH_PASSES = 6
R_MIN = 15.0         # m: the tightest turn
STR_LO, STR_RIDERS = 0.6, 4
HW_NEAR, HW_FAR = 1.7, 0.9
WIDTH_VAR, WIDTH_L = 0.3, 25.0
FADE_IN, FADE_OUT = 12.0, 30.0
TRENCH_WALL, SQUEEZE_HW, RAMP_STEPS = 1.1, 0.5, 3   # as game/src/pack/treeLines.ts (TRENCH_WALL, SQUEEZE_HW, RAMP_STEPS)
OPEN_D = 30.0        # m from any trunk: no forest
STALL_M = 30.0
SPACING_BAND = (3.0, 10.0)

DIRS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


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


def eligible(r):
    return bool(r.get("gladed") or (r.get("difficulty") in LINE_DIFF))


class Planner:
    def __init__(self, pack_dir, meta, features, log=print):
        from scipy.spatial import cKDTree
        import cover
        self.log = log
        self.meta, self.runs = meta, features.get("runs", [])
        self.hts = Heights(pack_dir, meta)
        tr = [t[:, :2] for t in cover.tree_records(pack_dir, meta)]
        self.trunks = np.concatenate(tr).astype(np.float64) if tr else np.zeros((0, 2))
        self.kd = cKDTree(self.trunks) if len(self.trunks) else None
        b = meta["bounds"]
        self.gx0, self.gy1 = float(b["minX"]), float(b["maxY"])
        self.occ = {}       # global cell (col, row) -> (line id, point index)
        self.lines = []     # each: dict(xy=[(x, y)...], riders=np.array, join=(id, idx) or None, seed kind)

    # -- per-run field -------------------------------------------------------------------------------------------------
    def window(self, p):
        x0 = math.floor((p[:, 0].min() - PAD - self.gx0) / RES) * RES + self.gx0
        y1 = self.gy1 - math.floor((self.gy1 - p[:, 1].max() - PAD) / RES) * RES
        x1 = p[:, 0].max() + PAD; y0 = p[:, 1].min() - PAD
        w = int(math.ceil((x1 - x0) / RES)); h = int(math.ceil((y1 - y0) / RES))
        return x0, y1, w, h

    def trunk_dist(self, x0, y1, w, h):
        xs = x0 + (np.arange(w) + 0.5) * RES; ys = y1 - (np.arange(h) + 0.5) * RES
        X, Y = np.meshgrid(xs, ys)
        if self.kd is None:
            return np.full((h, w), np.inf)
        d, _ = self.kd.query(np.column_stack([X.ravel(), Y.ravel()]), distance_upper_bound=OPEN_D + 5)
        return d.reshape(h, w)

    def run_masks(self, ri, x0, y1, w, h, foot_z):
        """walls (every run corridor but a gladed run's) and exits (this run's foot, any run lower than its foot)"""
        walls = Image.new("L", (w, h), 0); exits = Image.new("L", (w, h), 0)
        dw, de = ImageDraw.Draw(walls), ImageDraw.Draw(exits)
        px = lambda q: ((q[0] - x0) / RES, (y1 - q[1]) / RES)
        for j, r in enumerate(self.runs):
            pts = r["points"]
            if len(pts) < 2:
                continue
            xs = [q[0] for q in pts]; ys = [q[1] for q in pts]
            if max(xs) < x0 or min(xs) > x0 + w * RES or max(ys) < y1 - h * RES or min(ys) > y1:
                continue
            hw = RUN_KEEP.get(r.get("difficulty") or "", 10)
            wpx = max(1, int(round(2 * hw / RES)))
            if not r.get("gladed"):
                if r.get("area") and len(pts) >= 3:
                    dw.polygon([px(q) for q in pts], fill=255)
                else:
                    dw.line([px(q) for q in pts], fill=255, width=wpx, joint="curve")
            if j == ri:
                rl = run_line(r)
                if rl:
                    p, s = rl
                    keep = s >= s[-1] - FOOT_M
                    i0 = max(0, int(np.argmax(keep)) - 1)
                    de.line([px(q) for q in p[i0:]], fill=255, width=wpx + 2, joint="curve")
            else:
                # a run lower than this one's foot: getting onto it is getting out
                for a, b in zip(pts, pts[1:]):
                    if a[2] < foot_z and b[2] < foot_z:
                        de.line([px(a), px(b)], fill=255, width=wpx + 2)
        return np.asarray(walls) > 0, np.asarray(exits) > 0

    def field(self, z, dist, walls, exits):
        """the cost to get out from each cell (inf where there is no way), and the edge cost function's inputs"""
        from scipy import ndimage
        from scipy.sparse import csr_matrix
        from scipy.sparse.csgraph import dijkstra
        h, w = z.shape
        zf = np.where(np.isfinite(z), z, np.nanmax(z) if np.isfinite(z).any() else 0)
        zs = ndimage.gaussian_filter(zf.astype(np.float64), SMOOTH / RES, mode="nearest")
        gr, gc = np.gradient(zs, RES)
        # x east = +col, y north = -row: the fall line (downhill) is -grad
        gx, gy = gc, -gr
        g = np.hypot(gx, gy)
        fx, fy = -gx / np.maximum(g, 1e-9), -gy / np.maximum(g, 1e-9)
        ang_w = smooth(ANGLE_LO, ANGLE_HI, g)
        self.join_r = np.rint(JOIN + (JOIN_FLAT - JOIN) * (1 - smooth(STALL_TAN, FUNNEL_TAN, g))).astype(np.int64)
        tree = 1 + TREE_K * (1 - smooth(BLOCK, CLEAR, dist))
        if walls.any():
            tree = tree * (1 + EDGE_K * (1 - smooth(0, EDGE_M, ndimage.distance_transform_edt(~walls) * RES)))
        ok = np.isfinite(z) & (dist >= BLOCK) & (~walls | exits)
        idx = np.arange(h * w).reshape(h, w)
        rows, cols, wts = [], [], []
        self.cost = {}
        for di, dj in DIRS:
            a = (slice(max(0, -di), h - max(0, di)), slice(max(0, -dj), w - max(0, dj)))
            b = (slice(max(0, di), h - max(0, -di)), slice(max(0, dj), w - max(0, -dj)))
            L = RES * math.hypot(di, dj)
            ux, uy = dj / math.hypot(di, dj), -di / math.hypot(di, dj)
            drop = zs[a] - zs[b]
            cos = ux * fx[a] + uy * fy[a]
            c = L * (1 + ANGLE_K * (1 - cos) * ang_w[a]) * (1 + FLAT_K * (1 - smooth(0.0, STALL_TAN, drop / L))) * tree[b]
            c = c + RISE_K * np.maximum(0, -drop)
            good = ok[a] & ok[b]
            full = np.full((h, w), np.inf); full[a] = np.where(good, c, np.inf)
            self.cost[(di, dj)] = full
            # the reversed edge b -> a, so the search from the exits finds each cell's cost to get out
            rows.append(idx[b][good]); cols.append(idx[a][good]); wts.append(c[good])
        G = csr_matrix((np.concatenate(wts), (np.concatenate(rows), np.concatenate(cols))), shape=(h * w, h * w))
        src = idx[exits & ok]
        if not len(src):
            return np.full((h, w), np.inf), zs
        T = dijkstra(G, directed=True, indices=src, min_only=True)
        return T.reshape(h, w), zs

    # -- seeds and riders ----------------------------------------------------------------------------------------------
    def seeds(self, ri, r, p, s):
        trees = bool(r.get("gladed")) or r.get("difficulty") in TREE_RUN
        gap = SEED_GAP_TREES if trees else SEED_GAP
        rng = np.random.default_rng(int(r.get("osmId") or ri) & 0x7FFFFFFF)
        cand = []
        n = int(SEEDS_MAX * 20)
        for _ in range(n):
            q = rng.uniform(0, s[-1] * SEED_SPAN)
            u = rng.uniform()
            off = OFF_MIN + (OFF_MAX - OFF_MIN) * u * u   # most near the run's edge
            side = 1 if rng.uniform() < 0.5 else -1
            x, y, tx, ty = along(p, s, q)
            cand.append((x - ty * off * side, y + tx * off * side, 0.0))
        keep = []
        for c in cand:
            if all((c[0] - k[0]) ** 2 + (c[1] - k[1]) ** 2 >= gap * gap for k in keep):
                keep.append(c)
            if len(keep) >= SEEDS_MAX:
                break
        if trees:
            for e in range(ENTRY_LINES):
                side = 1 if (e + (1 if h01(ri, e, 1) < 0.5 else 0)) % 2 else -1
                x, y, tx, ty = along(p, s, ENTRY_S0 + ENTRY_DS * e)
                off = ENTRY_OFF + ENTRY_DOFF * e + 2 * h01(ri, e, 2)
                keep.append((x - ty * off * side, y + tx * off * side, ENTRY_OPEN))
        return keep

    def trace(self, T, x0, y1, w, h, sx, sy, rng):
        c, rr = int((sx - x0) / RES), int((y1 - sy) / RES)
        if not (0 <= rr < h and 0 <= c < w) or not np.isfinite(T[rr, c]):
            # the seed sits on a trunk or a wall: the nearest reachable cell within 3 cells
            best = None
            for dr in range(-3, 4):
                for dc in range(-3, 4):
                    a, b = rr + dr, c + dc
                    if 0 <= a < h and 0 <= b < w and np.isfinite(T[a, b]) and (best is None or dr * dr + dc * dc < best[0]):
                        best = (dr * dr + dc * dc, a, b)
            if not best:
                return [], None
            _, rr, c = best
        cells, seen = [], set()
        gc0 = int(round((x0 - self.gx0) / RES)); gr0 = int(round((self.gy1 - y1) / RES))
        for _ in range(MAX_STEPS):
            cells.append((rr, c)); seen.add((rr, c))
            # a ridden line here (nearer the flatter it is): join it
            jr = int(self.join_r[rr, c])
            for dr in range(-jr, jr + 1):
                for dc in range(-jr, jr + 1):
                    if dr * dr + dc * dc > jr * jr + 1:
                        continue
                    j = self.occ.get((gc0 + c + dc, gr0 + rr + dr))
                    if j is not None:
                        self.why = "join"
                        return cells, j
            if T[rr, c] <= 0:
                self.why = "exit"
                return cells, None
            best, bv = None, math.inf
            for di, dj in DIRS:
                a, b = rr + di, c + dj
                if not (0 <= a < h and 0 <= b < w) or (a, b) in seen:
                    continue
                e = self.cost[(di, dj)][rr, c]
                if not np.isfinite(e) or not np.isfinite(T[a, b]):
                    continue
                v = T[a, b] + e * (1 + NOISE * rng.standard_normal())
                if v < bv:
                    bv, best = v, (a, b)
            if best is None or T[best] >= T[rr, c] + 2 * RES:
                self.why = "stuck" if best is None else "uphill"
                return cells, None   # stalled
            rr, c = best
        self.why = "long"
        return cells, None

    def plan(self, only=None):
        order = sorted((i for i, r in enumerate(self.runs) if eligible(r) and run_line(r)),
                       key=lambda i: (-run_line(self.runs[i])[0][0, 2], i))
        for ri in order:
            r = self.runs[ri]
            if only and only.lower() not in (r.get("name") or "").lower():
                continue
            p, s = run_line(r)
            x0, y1, w, h = self.window(p)
            z = self.hts.window(x0, y1, w, h, RES)
            if not np.isfinite(z).any():
                continue
            dist = self.trunk_dist(x0, y1, w, h)
            walls, exits = self.run_masks(ri, x0, y1, w, h, float(p[-1, 2]))
            T, zs = self.field(z, dist, walls, exits)
            rng = np.random.default_rng((int(r.get("osmId") or ri) * 7919) & 0x7FFFFFFF)
            sd = self.seeds(ri, r, p, s)
            zsd = []
            for (sx, sy, op) in sd:
                cc, rr = int((sx - x0) / RES), int((y1 - sy) / RES)
                zsd.append(zs[rr, cc] if 0 <= rr < h and 0 <= cc < w else -1e9)
            gc0 = int(round((x0 - self.gx0) / RES)); gr0 = int(round((self.gy1 - y1) / RES))
            n0 = len(self.lines)
            self.whys = {}
            for k in np.argsort(-np.asarray(zsd), kind="stable"):
                sx, sy, op = sd[k]
                cells, join = self.trace(T, x0, y1, w, h, sx, sy, rng)
                if not cells:
                    continue
                xy = [(x0 + (cc + 0.5) * RES, y1 - (rr + 0.5) * RES) for rr, cc in cells]
                if join is not None and len(cells) * RES < MIN_LEN:
                    # a stub onto a ridden line: its rider rides that line, and nobody joins the stub (it is left out)
                    self.add_rider(join)
                    self.whys[self.why] = self.whys.get(self.why, 0) + 1
                    continue
                lid = len(self.lines)
                self.lines.append({"xy": xy, "riders": np.ones(len(xy)), "join": join, "open": op, "run": ri, "exit": join is None})
                if join is not None:
                    self.add_rider(join)
                self.whys[self.why] = self.whys.get(self.why, 0) + 1
                for i, (rr, cc) in enumerate(cells):
                    self.occ.setdefault((gc0 + cc, gr0 + rr), (lid, i))
            self.log(f"    {r.get('name') or '(unnamed)'} ({r.get('difficulty')}): {len(sd)} riders, {len(self.lines) - n0} lines, ends {self.whys}")

    def add_rider(self, join):
        while join is not None:
            lid, i = join
            ln = self.lines[lid]
            ln["riders"][i:] += 1
            join = ln["join"]

    # -- smooth and export ---------------------------------------------------------------------------------------------
    def shape(self, ln):
        xy = np.asarray(ln["xy"], np.float64)
        tail = None
        if ln["join"] is not None:
            pl = self.lines[ln["join"][0]]
            tail = np.asarray(pl["xy"][ln["join"][1]], np.float64)
            xy = np.vstack([xy, tail])
        rd = np.concatenate([ln["riders"], ln["riders"][-1:]]) if tail is not None else ln["riders"]
        seg = np.hypot(*np.diff(xy, axis=0).T)
        s = np.concatenate([[0.0], np.cumsum(seg)])
        if s[-1] < MIN_LEN:
            return None
        n = max(2, int(round(s[-1] / STEP)) + 1)
        q = np.linspace(0, s[-1], n)
        P = np.column_stack([np.interp(q, s, xy[:, 0]), np.interp(q, s, xy[:, 1])])
        R = np.interp(q, s, rd)
        # smooth with the ends held (the grid's 45-degree steps out, a Catmull-Rom-like curve left)
        for _ in range(SMOOTH_PASSES):
            P[1:-1] = 0.25 * P[:-2] + 0.5 * P[1:-1] + 0.25 * P[2:]
        # curvature clamp: a point turning tighter than R_MIN moves toward its neighbours' midpoint
        lim = STEP / R_MIN
        for _ in range(60):
            d1 = P[1:-1] - P[:-2]; d2 = P[2:] - P[1:-1]
            a = np.abs(np.arctan2(d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0], (d1 * d2).sum(1)))
            bad = np.nonzero(a > lim)[0]
            if not len(bad):
                break
            m = 0.5 * (P[bad] + P[bad + 2])
            P[bad + 1] = 0.5 * P[bad + 1] + 0.5 * m
        return P, R, q

    def export(self):
        out = []
        stats = {"broken": 0, "squeezed": 0, "trunksIn": 0}
        for ln in self.lines:
            sh = self.shape(ln)
            if sh is None:
                continue
            P, R, q = sh
            n = len(P)
            L = q[-1]
            str_ = STR_LO + (1 - STR_LO) * smooth(1, STR_RIDERS, R)
            salt = len(out) * 7919 + ln["run"]
            str_ = str_ * smooth(0, FADE_IN, q)
            if ln["exit"]:
                str_ = str_ * (1 - smooth(L - FADE_OUT, L, q))
            wander = 1 + WIDTH_VAR * np.interp(q / WIDTH_L, np.arange(int(L / WIDTH_L) + 3),
                                               [2 * h01(salt, i) - 1 for i in range(int(L / WIDTH_L) + 3)])
            hw = (HW_FAR + (HW_NEAR - HW_FAR) * str_) * wander
            hw = np.maximum(hw, SQUEEZE_HW)
            str_ = np.asarray(str_, np.float64)
            # the trunks: squeeze, and break where even a squeezed corridor hits one
            if self.kd is not None:
                mid = 0.5 * (P[:-1] + P[1:])
                broke = []
                for i in range(n - 1):
                    if str_[i] <= 0.02:
                        continue
                    a, b = P[i], P[i + 1]
                    for t in self.kd.query_ball_point(mid[i], hw[i] + TRENCH_WALL + STEP):
                        d = seg_dist(self.trunks[t], a, b)
                        if d < hw[i] + TRENCH_WALL:
                            if d - TRENCH_WALL < SQUEEZE_HW:
                                broke.append(i)
                            else:
                                hw[i] = min(hw[i], d - TRENCH_WALL); stats["squeezed"] += 1
                for i in broke:
                    str_[i] = 0
                    for k in range(1, RAMP_STEPS + 1):
                        f = k / (RAMP_STEPS + 1)
                        if i - k >= 0: str_[i - k] = min(str_[i - k], f)
                        if i + k < n - 1: str_[i + k] = min(str_[i + k], f)
                stats["broken"] += len(set(broke))
                # no forest round it: nothing to wear (an entrance's open start stays)
                dn, _ = self.kd.query(P, distance_upper_bound=OPEN_D)
                bare = ~np.isfinite(dn) & (q > ln["open"])
                str_[bare] = 0
            # split at the gaps, trim the zero ends
            on = str_ > 0.02
            i = 0
            while i < n:
                if not on[i]:
                    i += 1; continue
                j = i
                while j + 1 < n and on[j + 1]:
                    j += 1
                a, b = max(0, i - 1), min(n - 1, j + 1)
                if q[b] - q[a] >= MIN_LEN:
                    pts = []
                    for k in range(a, b + 1):
                        pts += [round(float(P[k, 0]), 2), round(float(P[k, 1]), 2), round(float(hw[k]), 2), round(float(str_[k]) if a < k < b else 0.0, 3)]
                    e = {"p": pts}
                    op = ln["open"] - q[a]
                    if op > 0:
                        e["open"] = round(float(op), 1)
                    out.append(e)
                i = j + 1
        return out, stats


def seg_dist(pt, a, b):
    d = b - a; l2 = float(d @ d)
    t = 0.0 if l2 <= 0 else min(1.0, max(0.0, float((pt - a) @ d) / l2))
    e = a + d * t - pt
    return math.hypot(e[0], e[1])


def validate(lines, planner):
    """trunks inside a corridor (0 is the rule), stall stretches, spacing between neighbouring lines"""
    from scipy.spatial import cKDTree
    inside, stalls, km = 0, 0, 0.0
    pts, owner = [], []
    for li, ln in enumerate(lines):
        p = np.asarray(ln["p"], np.float64).reshape(-1, 4)
        seg = np.hypot(*np.diff(p[:, :2], axis=0).T); km += seg.sum() / 1000
        if planner.kd is not None:
            for i in range(len(p) - 1):
                if p[i, 3] < 0.15:
                    continue
                for t in planner.kd.query_ball_point(0.5 * (p[i, :2] + p[i + 1, :2]), p[i, 2] + STEP):
                    if seg_dist(planner.trunks[t], p[i, :2], p[i + 1, :2]) < p[i, 2]:
                        inside += 1
        # stall: the ground along the line flatter than STALL_TAN for over STALL_M m
        x0, x1 = p[:, 0].min() - 4, p[:, 0].max() + 4
        y0, y1 = p[:, 1].min() - 4, p[:, 1].max() + 4
        w, h = int(math.ceil((x1 - x0) / RES)), int(math.ceil((y1 - y0) / RES))
        z = planner.hts.window(x0, y1, w, h, RES)
        c = np.clip(((p[:, 0] - x0) / RES).astype(int), 0, w - 1); r = np.clip(((y1 - p[:, 1]) / RES).astype(int), 0, h - 1)
        zz = z[r, c]
        run = 0.0
        for i in range(len(p) - 1):
            flat = np.isfinite(zz[i]) and np.isfinite(zz[i + 1]) and (zz[i] - zz[i + 1]) < STALL_TAN * seg[i]
            run = run + seg[i] if flat else 0.0
            if flat and run > STALL_M and run - seg[i] <= STALL_M:
                stalls += 1
        strong = p[:, 3] >= 0.3
        pts.append(p[strong, :2]); owner.append(np.full(int(strong.sum()), li))
    spacing = None
    if pts and sum(len(a) for a in pts) > 10:
        P = np.concatenate(pts); O = np.concatenate(owner)
        kd = cKDTree(P)
        d, j = kd.query(P, k=min(12, len(P)))
        near = np.full(len(P), np.inf)
        for col in range(1, d.shape[1]):
            have = j[:, col] < len(P)
            other = have & (O[np.minimum(j[:, col], len(P) - 1)] != O)
            near = np.where(np.isinf(near) & other & np.isfinite(d[:, col]), d[:, col], near)
        f = np.isfinite(near) & (near < 40)
        if f.any():
            lo, hi = SPACING_BAND
            spacing = {"median": round(float(np.median(near[f])), 1), "inBand": round(float(np.mean((near[f] >= lo) & (near[f] <= hi))), 3)}
    return {"km": round(km, 1), "trunksInCorridor": inside, "stalls": stalls, "spacing": spacing}


def build_tree_lines(pack_dir, meta, features=None, only=None, log=print):
    """write treeLines.json and return the meta entry (None when no run gets lines)"""
    if features is None:
        features = json.load(open(os.path.join(pack_dir, "features.json"), encoding="utf-8"))
    pl = Planner(pack_dir, meta, features, log=log)
    pl.plan(only=only)
    lines, st = pl.export()
    if not lines:
        log("  tree lines: none")
        p = os.path.join(pack_dir, FILE)
        if os.path.exists(p):
            os.remove(p)
        return None
    chk = validate(lines, pl)
    path = os.path.join(pack_dir, FILE)
    with open(path, "w") as f:
        json.dump({"version": VERSION, "step": STEP, "lines": lines}, f, separators=(",", ":"))
    sp = chk["spacing"] or {}
    log(f"  tree lines: {len(lines)} lines, {chk['km']} km from {len(pl.lines)} riders' traces, {st['squeezed']} squeezes and "
        f"{st['broken']} breaks at a trunk, {chk['trunksInCorridor']} trunks in a corridor, {chk['stalls']} stall stretches "
        f"over {STALL_M:g} m, spacing median {sp.get('median')} m ({(sp.get('inBand') or 0) * 100:.0f}% in "
        f"{SPACING_BAND[0]:g} to {SPACING_BAND[1]:g} m); {os.path.getsize(path) / 1e3:.0f} KB")
    return {"file": FILE, "lines": len(lines), "km": chk["km"], "checks": chk}


def main(argv):
    if not argv or argv[0].startswith("-"):
        sys.exit(__doc__)
    pack_dir = argv[0]
    only = argv[argv.index("--only") + 1] if "--only" in argv else None
    mp = os.path.join(pack_dir, "meta.json")
    meta = json.load(open(mp, encoding="utf-8"))
    e = build_tree_lines(pack_dir, meta, only=only)
    if e:
        meta["treeLines"] = e
    else:
        meta.pop("treeLines", None)
    from packwriter import stamp_build
    stamp_build(meta)
    with open(mp, "w") as f:
        json.dump(meta, f, indent=1)


if __name__ == "__main__":
    main(sys.argv[1:])
