#!/usr/bin/env python3
"""Traffic map (FEAT-379): where riders go, which way and how much, for the game's old tracks (SnowboardAnywhere
FEAT-380), simulated once at build time like the tree lines (FEAT-334).

python pipeline/traffic.py packs/<slug> [--view x0,y0,x1,y1 out.png]

Writes traffic/<tx>_<ty>.png and the `traffic` entry of meta.json. Runs standalone on a built pack (no raw data, no
rebuild) and from build_pack.py after the tree lines, whose treeLines.json it reads. --view draws a built map over the
hillshade in a box of local metres (density as colour, the mean direction as ticks) and writes nothing to the pack.

On a RES m grid over the pack bounds, anchored on the mask's south-west corner:
  1. Ground. The coarse heights (4 m; the fine ones averaged when a pack has none), smoothed over SMOOTH m for the fall
     line. The mask's groomed (B) and canopy (A) channels, averaged to RES.
  2. Runs. Every downhill run's centre line, downhill first, sampled every metre and burned into the grid: its tangent
     (the downhill sense along the line, averaged over TAN_M m), its bend (signed curvature over BEND_M m), its arc
     position and its kind. A stretch whose line drops less than TRACK_K of the ground's slope across it, or under
     TRACK_TAN, and is gentler than TRACK_MAX, is a cat track or traverse (along its axis, in a few lanes); otherwise a groomed run is a groomer and an
     ungroomed or gladed one off-piste. Each kind's ridden half-width there: a groomer's and a cat track's from the
     groomed mask (the distance from the line to the edge of the corduroy, so trees closing in narrow it), off-piste
     from the canopy (how far the open snow reaches), a gladed run GLADE_HW. Every cell takes the nearest line cell's
     record (a distance transform).
  3. Tree lines. The pack's treeLines.json (whatever traced it) deposited along each line, its strength the riders, and
     the same deposit blurred into a pull that draws off-piste riders onto the lines near them.
  4. Riders. Released at each lift's top in proportion to its capacity (CAPACITY by lift type where the data has
     none), shared between the runs that start within LIFT_RUNS m of it (the lift exit: each rider first heads for the
     start it picked; a lift or run starting past the bounds releases where the run comes in), plus RUN_RIDERS at
     every run's top. Each step (STEP m) a rider steers for a point LOOK m down the
     nearest run's line, at its own lateral lane times the run's spread: a groomer LANE_GROOMED of its half-width (a
     broad peak, fewer toward the edges), a cat track two or three lanes cutting the inside of bends, off-piste
     LANE_OFF of its open width, fanning out from the entry and narrowing to the exit over FAN_IN / FAN_OUT m. So
     riders merge where runs join and funnel where a run narrows. Off-piste they lean to the fall line and onto a tree
     line nearby; off the network they follow the fall line. Near a lift's bottom station a rider that takes that lift
     (BOARD, the lowest lifts and where no run goes on always) is drawn to it and stops there. A rider also stops past the bounds, after
     MAX_STEPS, climbing more than UPHILL m, or stalled on the flat off the runs. Lanes wander (correlated over
     LANE_L m) and each rider's heading carries a little noise, so no two ride the same line.
  5. Accumulate. Every step deposits its rider's travel direction, swung by the rider's turns (TURN_DEG by kind, a
     carving groomer wider than a cat track), into the cell; the density and the vector sum are blurred with a Gaussian
     KERNEL m kernel, so density falls off smoothly. The mean direction is the vector sum over the density: its length
     is the coherence (1 = everyone the same way).
Pure: the same pack gives the same map.

Tiles: RGB PNG, TILE px on RES m (1024 m, the mask's tile): R, G = the mean direction x east, y north, each byte
(v * 0.5 + 0.5) * 255; B = density, 255 * (1 - exp(-sqrt(c / c_ref))) with c_ref the DENSITY_PCT percentile of the ridden
cells (a pack's own busiest runs saturate). Where B is 0, R = G = 128. See docs/pack-format.md.
"""
import json, math, os, sys, time
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tree_lines import smooth as smoothstep, Heights   # noqa: E402

KIND = "traffic"
RES = 4.0            # m per texel
TILE = 256           # px per tile: 1024 m, the mask's 512 px at 2 m
SMOOTH = 8.0         # m: Gaussian sigma of the heights for the fall line and the slope a cat track is measured against
SAMPLE = 1.0         # m between a run line's samples
MIN_RUN = 10.0       # m: a shorter run line (a connector) is left out
TAN_M = 12.0         # m: a line's tangent is the chord over this
BEND_M = 20.0        # m: a line's bend is the turn of its tangent over this
TRACK_K = 0.45       # a line dropping less than this share of the ground's slope traverses it
TRACK_G = 0.12       # ... on ground at least this steep
TRACK_TAN = 0.06     # a line flatter than this is a track whatever the ground
TRACK_MAX = 0.14     # ... and a traverse steeper than this is a run (a cat track is a gentle road)
TRACK_M = 40.0       # m: the cat track call is a majority over this much line
HW_GROOMED = (4.0, 40.0)    # m: a groomer's ridden half-width, clamped
HW_TRACK = (3.0, 12.0)      # m: a cat track's
HW_OFF = (15.0, 60.0)       # m: an off-piste run's open width
GLADE_HW = 30.0
CANOPY = 0.35        # mask A over this is forest (the open width ends there)
GROOMED = 0.3        # mask B over this is corduroy
REACH = 40.0         # m: a rider within the larger of this and 2.5 times a run's spread follows the run
LOOK = 10.0          # m: how far down the line a rider aims
LANE_GROOMED = 0.42  # lane sigma, times the half-width
LANE_TRACK, LANE_TRACK_JIT = 0.42, 0.12   # cat track lanes (-1, 0, 1 times this) and the jitter round each
LANE_OFF = 0.7
LANE_L = 250.0       # m: a lane's correlation length
BEND_R = 40.0        # m: a bend this tight or tighter moves the lanes BEND of the half-width to its inside
BEND = {0: 0.15, 1: 0.3, 2: 0.1}
FAN_MIN, FAN_IN, FAN_OUT = 0.2, 120.0, 150.0
FALL_W = 0.35        # off-piste: the fall line's weight against the line
FALL_LO, FALL_HI = 0.03, 0.15   # slope (tan) over which the fall line takes over off the network
TL_RIDERS = 3.0      # riders a tree line of strength 1 stands for
TL_PULL = 0.6
TL_LO, TL_HI = 0.03, 0.3        # tree line deposit (blurred, per cell) over which the pull starts and is full
INERTIA = 0.55
HEAD_NOISE = 0.06    # rad per step
STEP = 4.0
MAX_STEPS = 2500
UPHILL = 8.0         # m
STALL_STEPS = 40
LIFT_RIDERS = 9000   # riders shared between the lifts by capacity
CAPACITY = {"gondola": 2400, "cable_car": 1000, "chair_lift": 1800, "mixed_lift": 2400, "drag_lift": 800,
            "t-bar": 800, "j-bar": 500, "platter": 600, "rope_tow": 400, "magic_carpet": 300}
CAPACITY_DEFAULT = 1200
LIFT_RUNS = 150.0    # m: runs that start this near a lift's top share its riders
LIFT_RUNS_FAR = 600.0  # m: ... or this near, for a lift whose top is past the bounds
POPULAR = {"novice": 0.8, "easy": 0.9, "intermediate": 1.0, "advanced": 0.6, "expert": 0.35, "freeride": 0.3, "extreme": 0.2}
RUN_RIDERS = 3
SINK_R = 100.0       # m: a lift's bottom station draws the riders who take it from this far
SINK_STOP = 8.0
BOARD = 0.55
MIN_RIDE = 30        # steps before a rider can board
TURN_DEG = {0: 45.0, 1: 10.0, 2: 50.0}
TURN_L = 18.0        # m per turn (half a period)
KERNEL = 5.0         # m: the accumulation kernel's sigma
RIDDEN_C = 0.05      # blurred rider steps over which a cell counts as ridden for c_ref
DENSITY_PCT = 90.0   # c_ref: this percentile of the ridden cells reads 0.63; the square root lifts the quiet runs
SEED = 379
LINE_SLOPE_M = 30.0  # m: a run line's own drop is measured over this
REACH_K = 2.5        # ... a rider follows a run out to REACH_K times its spread (at least REACH)
ARRIVE = 8.0         # m: a rider heading for a run's start from a lift has got there
FLAT_FALL = 0.05     # fall line weight under which the ground counts as flat (off the network: stall)
JITTER = 3.0         # m: sigma of the release points round a lift top or run top
TOP_SLACK = 15.0     # m: a run that starts this far above a lift's top still takes its riders
HW_OFF_NOMASK = 30.0 # m: an off-piste run's open half-width in a pack without a mask
TL_SAMPLE = 2.0      # m between a tree line's deposits
TL_BLUR = 6.0        # m: the tree line pull's blur
TL_GRAD = 0.8        # the pull toward a tree line's middle against along it


def unit(x, y):
    n = np.maximum(np.hypot(x, y), 1e-9)
    return x / n, y / n


class Grid:
    """the traffic grid: W x H cells of RES m from (minX, minY), row 0 = north"""
    def __init__(self, meta):
        m, b = meta["mask"], meta["bounds"]
        self.x0, self.y0 = float(m["minX"]), float(m["minY"])
        self.W = int(math.ceil((b["maxX"] - self.x0) / RES))
        self.H = int(math.ceil((b["maxY"] - self.y0) / RES))
        self.yT = self.y0 + self.H * RES

    def cell(self, x, y):
        return ((self.yT - y) / RES).astype(np.int64), ((x - self.x0) / RES).astype(np.int64)

    def inside(self, rr, cc):
        return (rr >= 0) & (rr < self.H) & (cc >= 0) & (cc < self.W)


def read_heights(pack_dir, meta, g):
    """heights at the grid's cell centres (the coarse set's own samples when it has one)"""
    t = meta["terrain"]
    c = t.get("coarse")
    if c and c["res"] == RES and c["minX"] == g.x0 and c["minY"] == g.y0:
        from packwriter import decode_terrarium
        n = c["tileSize"]
        z = np.full((c["tilesY"] * n, c["tilesX"] * n), np.nan, np.float32)
        for ty in range(c["tilesY"]):
            for tx in range(c["tilesX"]):
                p = os.path.join(pack_dir, "coarse", f"{tx}_{ty}.png")
                if os.path.exists(p):
                    r0 = (c["tilesY"] - 1 - ty) * n
                    z[r0:r0 + n, tx * n:(tx + 1) * n] = decode_terrarium(np.asarray(Image.open(p).convert("RGB")))
        Hp = z.shape[0]
        z = z[Hp - g.H:, :g.W]
        if z.shape == (g.H, g.W):
            return np.where(z < -30000, np.nan, z)
    return Heights(pack_dir, meta).window(g.x0, g.yT, g.W, g.H, RES)


def read_mask(pack_dir, meta, g):
    """groomed (B) and canopy (A) averaged to the grid, or (None, None) without a mask"""
    m = meta.get("mask")
    if not m or not os.path.isdir(os.path.join(pack_dir, "mask")):
        return None, None
    k = int(round(RES / m["res"]))
    n = m["tileSize"]
    Hp, Wp = m["tilesY"] * n, m["tilesX"] * n
    if Hp < g.H * k or Wp < g.W * k:
        return None, None
    ba = np.zeros((Hp, Wp, 2), np.uint8)
    for ty in range(m["tilesY"]):
        for tx in range(m["tilesX"]):
            p = os.path.join(pack_dir, "mask", f"{tx}_{ty}.png")
            if os.path.isfile(p):
                r0 = (m["tilesY"] - 1 - ty) * n
                ba[r0:r0 + n, tx * n:(tx + 1) * n] = np.asarray(Image.open(p).convert("RGBA"))[..., 2:4]
    ba = ba[Hp - g.H * k:, :g.W * k]
    acc = np.zeros((g.H, g.W, 2), np.uint16)
    for i in range(k):
        for j in range(k):
            acc += ba[i::k, j::k]
    ba = acc.astype(np.float32) / (255 * k * k)
    return ba[..., 0], ba[..., 1]


def across(grid, x, y, nx, ny, g, inside, hw_max):
    """for each line sample, how far (m) the `inside` test holds along its normal to the left and to the right"""
    out = []
    for sgn in (1, -1):
        reach = np.zeros(len(x)); alive = np.ones(len(x), bool)
        for d in np.arange(RES / 2, hw_max + 1e-6, RES / 2):
            rr, cc = g.cell(x + sgn * nx * d, y + sgn * ny * d)
            ok = g.inside(rr, cc)
            v = np.zeros(len(x), bool)
            v[ok] = inside(grid[rr[ok], cc[ok]])
            alive &= v
            reach = np.where(alive, d, reach)
            if not alive.any():
                break
        out.append(reach)
    return out


def run_samples(runs, g, zs_slope):
    """every run line sampled every SAMPLE m: position, tangent, bend, arc position, kind and the line's own slope"""
    rows = []
    for ri, r in enumerate(runs):
        if r.get("pisteType") or r.get("area"):
            continue
        p = np.asarray(r["points"], np.float64)
        if len(p) < 2 or p.shape[1] < 3:
            continue
        p = p[::-1] if p[0, 2] < p[-1, 2] else p   # downhill first (tree_lines.run_line drops the short connectors)
        s = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(p[:, 0]), np.diff(p[:, 1])))])
        L = s[-1]
        if L < MIN_RUN:
            continue
        q = np.arange(0, L + 1e-6, SAMPLE)
        x, y, z = (np.interp(q, s, p[:, i]) for i in range(3))
        n = len(q)
        k = max(1, int(round(TAN_M / 2 / SAMPLE)))
        i0, i1 = np.clip(np.arange(n) - k, 0, n - 1), np.clip(np.arange(n) + k, 0, n - 1)
        tx, ty = unit(x[i1] - x[i0], y[i1] - y[i0])
        kb = max(1, int(round(BEND_M / 2 / SAMPLE)))
        b0, b1 = np.clip(np.arange(n) - kb, 0, n - 1), np.clip(np.arange(n) + kb, 0, n - 1)
        turn = np.arctan2(tx[b0] * ty[b1] - ty[b0] * tx[b1], tx[b0] * tx[b1] + ty[b0] * ty[b1])
        bend = turn / np.maximum(q[b1] - q[b0], 1.0)
        # the line's own drop against the ground's slope across it
        kz = max(1, int(round(LINE_SLOPE_M / 2 / SAMPLE)))
        z0, z1 = np.clip(np.arange(n) - kz, 0, n - 1), np.clip(np.arange(n) + kz, 0, n - 1)
        line_tan = np.abs(z[z0] - z[z1]) / np.maximum(q[z1] - q[z0], 1.0)
        rr, cc = g.cell(x, y)
        ok = g.inside(rr, cc)
        gs = np.zeros(n); gs[ok] = zs_slope[rr[ok], cc[ok]]
        track = ((line_tan < TRACK_K * gs) & (gs > TRACK_G) & (line_tan < TRACK_MAX)) | (line_tan < TRACK_TAN)
        km = max(1, int(round(TRACK_M / SAMPLE)))
        from scipy.ndimage import uniform_filter1d
        track = uniform_filter1d(track.astype(np.float64), km, mode="nearest") > 0.5
        kind = np.where(track, 1, np.where(r.get("groomed") and not r.get("gladed"), 0, 2))
        rows.append(dict(x=x[ok], y=y[ok], tx=tx[ok], ty=ty[ok], bend=bend[ok], s=q[ok], L=np.full(ok.sum(), L),
                         kind=kind[ok], run=np.full(ok.sum(), ri), rr=rr[ok], cc=cc[ok],
                         pref=np.full(ok.sum(), 1 if r.get("groomed") else 0)))
    if not rows:
        return None
    return {k: np.concatenate([d[k] for d in rows]) for k in rows[0]}


class Field:
    """the grids the riders read"""
    def __init__(self, pack_dir, meta, features, log=print):
        from scipy import ndimage
        g = self.g = Grid(meta)
        H, W = g.H, g.W
        z = read_heights(pack_dir, meta, g)
        zf = np.where(np.isfinite(z), z, np.nanmax(z) if np.isfinite(z).any() else 0).astype(np.float32)
        self.z = zf.ravel()
        zs = ndimage.gaussian_filter(zf, SMOOTH / RES, mode="nearest")
        gr, gc = np.gradient(zs, RES)
        gx, gy = gc, -gr
        slope = np.hypot(gx, gy)
        w = smoothstep(FALL_LO, FALL_HI, slope).astype(np.float32)
        fx, fy = unit(-gx, -gy)
        self.fall = np.stack([(fx * w).ravel(), (fy * w).ravel()]).astype(np.float32)
        del gr, gc, gx, gy, fx, fy, w
        slope_wide = slope.astype(np.float32)
        del zs, slope
        groomed, canopy = read_mask(pack_dir, meta, g)
        self.runs = features.get("runs", [])
        S = run_samples(self.runs, g, slope_wide)
        del slope_wide
        self.lines = 0
        if S is not None:
            # burn the samples in, groomed runs last so they win where lines overlap
            o = np.argsort(S["pref"], kind="stable")
            S = {k: v[o] for k, v in S.items()}
            fi = S["rr"] * W + S["cc"]
            _, last = np.unique(fi[::-1], return_index=True)
            keep = len(fi) - 1 - last
            S = {k: v[keep] for k, v in S.items()}
            fi = fi[keep]
            n = len(fi)
            lid = np.full(H * W, -1, np.int32); lid[fi] = np.arange(n)
            line = (lid >= 0).reshape(H, W)
            d, (ri, ci) = ndimage.distance_transform_edt(~line, return_indices=True)
            self.near = lid.reshape(H, W)[ri, ci].ravel().astype(np.int32)
            self.near_d = (d * RES).astype(np.float32).ravel()
            del d, ri, ci, line, lid
            # ridden half-widths
            kind = S["kind"]
            from canopy_spots import run_half_width   # the build's corridor half-width, where the mask has none
            hw = np.array([run_half_width(self.runs[r]) for r in S["run"]], np.float64)
            mid = np.zeros(len(fi))   # the ridden corridor's centre, metres left of the OSM line
            if groomed is not None:
                nx, ny = -S["ty"], S["tx"]
                gl, gr_ = across(groomed, S["x"], S["y"], nx, ny, g, lambda v: v > GROOMED, HW_GROOMED[1])
                ol, or_ = across(canopy, S["x"], S["y"], nx, ny, g, lambda v: v <= CANOPY, HW_OFF[1])
                eg, eo = 0.5 * (gl + gr_), 0.5 * (ol + or_)
                hw = np.where(kind == 0, np.where(eg > 0, np.clip(eg, *HW_GROOMED), hw), hw)
                hw = np.where(kind == 1, np.where(eg > 0, np.clip(eg, *HW_TRACK), np.clip(hw, *HW_TRACK)), hw)
                hw = np.where(kind == 2, np.clip(eo, *HW_OFF), hw)
                mid = np.select([(kind != 2) & (eg > 0), kind == 2], [0.5 * (gl - gr_), 0.5 * (ol - or_)], 0.0)
                mid = np.clip(mid, -0.5 * hw, 0.5 * hw)
            else:
                hw = np.where(kind == 1, np.clip(hw, *HW_TRACK), np.where(kind == 2, HW_OFF_NOMASK, hw))
            glade = np.array([bool(self.runs[r].get("gladed")) for r in S["run"]])
            hw = np.where((kind == 2) & glade, GLADE_HW, hw)
            mid = np.where((kind == 2) & glade, 0.0, mid)
            fan = np.where(kind == 2, FAN_MIN + (1 - FAN_MIN) * smoothstep(0, FAN_IN, S["s"]) * smoothstep(0, FAN_OUT, S["L"] - S["s"]), 1.0)
            spread = np.select([kind == 0, kind == 1], [LANE_GROOMED * hw, LANE_TRACK * hw], LANE_OFF * hw * fan)
            S["hw"], S["spread"], S["mid"] = hw, spread, mid
            S["reach"] = np.maximum(REACH, REACH_K * spread)
            S["end"] = S["s"] >= S["L"] - 2 * SAMPLE
            self.S = S
            self.lines = len(set(S["run"].tolist()))
            self.kinds = {k: round(float((kind == i).sum() * RES) / 1000, 1) for i, k in enumerate(("groomer", "track", "off"))}
        else:
            self.S = None
        self.tree_lines(pack_dir, meta)
        self.lifts(features.get("lifts", []))

    def tree_lines(self, pack_dir, meta):
        """the baked tree lines as a deposit (cells, direction, riders) and the pull they have on riders near them"""
        from scipy import ndimage
        g = self.g
        f = os.path.join(pack_dir, (meta.get("treeLines") or {}).get("file") or "treeLines.json")
        self.tl = None
        self.pull = None
        if not os.path.exists(f):
            return
        fis, dxs, dys, ws = [], [], [], []
        for ln in json.load(open(f, encoding="utf-8")).get("lines", []):
            p = np.asarray(ln["p"], np.float64).reshape(-1, 4)
            if len(p) < 2:
                continue
            seg = np.hypot(*np.diff(p[:, :2], axis=0).T)
            s = np.concatenate([[0.0], np.cumsum(seg)])
            q = np.arange(0, s[-1], TL_SAMPLE)
            x, y, st = np.interp(q, s, p[:, 0]), np.interp(q, s, p[:, 1]), np.interp(q, s, p[:, 3])
            rr, cc = g.cell(x, y)
            ok = g.inside(rr, cc)
            if ok.sum() < 2:
                continue
            fi = rr * g.W + cc
            # the downhill sense, whichever way the file lists it
            if self.z[fi[ok][0]] < self.z[fi[ok][-1]]:
                x, y = x[::-1], y[::-1]; st = st[::-1]; fi = fi[::-1]; ok = ok[::-1]
            tx, ty = unit(np.gradient(x), np.gradient(y))
            fis.append(fi[ok]); dxs.append(tx[ok]); dys.append(ty[ok]); ws.append(st[ok] * TL_RIDERS)
        if not fis:
            return
        fi, dx, dy, w = (np.concatenate(a) for a in (fis, dxs, dys, ws))
        self.tl = (fi, dx, dy, w)
        # the pull, on the lines' own box (plus the blur's reach)
        r, c = fi // g.W, fi % g.W
        pad = int(4 * TL_BLUR / RES) + 2
        r0, r1 = max(0, r.min() - pad), min(g.H, r.max() + pad + 1)
        c0, c1 = max(0, c.min() - pad), min(g.W, c.max() + pad + 1)
        h, wd = r1 - r0, c1 - c0
        li = (r - r0) * wd + (c - c0)
        blur = lambda v: ndimage.gaussian_filter(np.bincount(li, v, h * wd).reshape(h, wd).astype(np.float32), TL_BLUR / RES)
        den, vx, vy = blur(w), blur(w * dx), blur(w * dy)
        gr, gc = np.gradient(den)
        ux, uy = unit(vx, vy); gx, gy = unit(gc, -gr)
        pw = (TL_PULL * smoothstep(TL_LO, TL_HI, den / TL_RIDERS)).astype(np.float32)
        self.pull = np.zeros((3, g.H, g.W), np.float32)
        self.pull[:, r0:r1, c0:c1] = np.stack([(ux + TL_GRAD * gx) * pw, (uy + TL_GRAD * gy) * pw, pw])
        self.pull = self.pull.reshape(3, -1)

    def lifts(self, lifts):
        """the release points (lift tops, by capacity) and the bottom stations that draw riders in"""
        g = self.g
        self.tops, self.bottoms = [], []
        for l in lifts:
            st = np.asarray(l.get("stations") or [], np.float64)
            if len(st) < 2 or st.shape[1] < 3:
                continue
            a, b = (st[0], st[-1]) if st[0, 2] >= st[-1, 2] else (st[-1], st[0])
            cap = l.get("capacity") or CAPACITY.get(l.get("type") or "", CAPACITY_DEFAULT)
            self.tops.append((a[0], a[1], a[2], float(cap)))
            self.bottoms.append((b[0], b[1], b[2]))
        H, W = g.H, g.W
        self.sink = None
        if self.bottoms:
            sid = np.full((H, W), -1, np.int32); sd = np.full((H, W), np.inf, np.float32)
            rad = int(math.ceil(SINK_R / RES))
            for i, (x, y, _) in enumerate(self.bottoms):
                r, c = int((g.yT - y) / RES), int((x - g.x0) / RES)
                r0, r1, c0, c1 = max(0, r - rad), min(H, r + rad + 1), max(0, c - rad), min(W, c + rad + 1)
                if r0 >= r1 or c0 >= c1:
                    continue
                Y = g.yT - (np.arange(r0, r1) + 0.5) * RES; X = g.x0 + (np.arange(c0, c1) + 0.5) * RES
                d = np.hypot(X[None, :] - x, Y[:, None] - y).astype(np.float32)
                win = (d < sd[r0:r1, c0:c1]) & (d <= SINK_R)
                sd[r0:r1, c0:c1][win] = d[win]; sid[r0:r1, c0:c1][win] = i
            self.sink = (sid.ravel(), sd.ravel())
            # the lowest lifts take everyone who gets there
            zb = np.array([b[2] for b in self.bottoms])
            self.last = zb <= np.percentile(zb, 25)


def release(F, rng):
    """the riders' start points, first targets and lanes"""
    S, runs = F.S, F.runs
    starts = []   # (x, y, goto x, goto y)
    # each run's top: its highest sample on the grid (a run may start past the bounds)
    tops = {}
    for i in np.argsort(-S["s"], kind="stable"):
        tops[int(S["run"][i])] = (S["x"][i], S["y"][i])
    tlist = list(tops.items())
    total_cap = sum(t[3] for t in F.tops) or 1.0
    for (x, y, z, cap) in F.tops:
        n = int(round(LIFT_RIDERS * cap / total_cap))
        on_grid = bool(F.g.inside(*F.g.cell(np.array([x]), np.array([y])))[0])
        cand = []
        # past the bounds there is no field to carry riders from the station: the run tops further off share them
        for reach in (LIFT_RUNS,) if on_grid else (LIFT_RUNS, LIFT_RUNS_FAR):
            for ri, (sx, sy) in tlist:
                p0 = np.asarray(runs[ri]["points"])[:, :3]
                top = p0[np.argmax(p0[:, 2])]
                if math.hypot(top[0] - x, top[1] - y) <= reach and top[2] <= z + TOP_SLACK:
                    cand.append((ri, sx, sy, POPULAR.get(runs[ri].get("difficulty") or "", 0.6)))
            if cand:
                break
        if cand:
            w = np.array([c[3] for c in cand]); w = w / w.sum()
            pick = rng.choice(len(cand), size=n, p=w)
            for k in pick:
                # the lift exit when the lift's top is on the grid, else straight onto the run
                starts.append((x, y, cand[k][1], cand[k][2]) if on_grid else (cand[k][1], cand[k][2], np.nan, np.nan))
        elif on_grid:
            starts += [(x, y, np.nan, np.nan)] * n
    for ri, (sx, sy) in tlist:
        starts += [(sx, sy, np.nan, np.nan)] * RUN_RIDERS
    if not starts:
        return None
    a = np.asarray(starts, np.float64)
    a[:, 0:2] += rng.normal(0, JITTER, (len(a), 2))
    return a


def simulate(F):
    """walk every rider; returns the deposit (cells, direction x, y, weight) and the end counts"""
    g = F.g
    rng = np.random.default_rng(SEED)
    st = None if F.S is None else release(F, rng)
    if st is None:
        return None, {}
    S = F.S
    N = len(st)
    x, y = st[:, 0].copy(), st[:, 1].copy()
    gx, gy = st[:, 2].copy(), st[:, 3].copy()
    going = np.isfinite(gx)
    hx, hy = np.zeros(N), np.full(N, -1.0)
    ux, uy = unit(gx - x, gy - y); hx[going], hy[going] = ux[going], uy[going]
    lane = rng.normal(0, 1, N)
    phase = rng.uniform(0, 2 * math.pi, N)
    nl = len(F.bottoms)
    board = rng.uniform(size=(N, max(nl, 1))) < BOARD
    if nl:
        board[:, :nl] |= F.last[None, :]
    zmin = np.full(N, np.inf)
    stall = np.zeros(N, np.int32)
    a_lane = STEP / LANE_L
    turn_k = np.array([math.radians(TURN_DEG[k]) for k in (0, 1, 2)] + [math.radians(TURN_DEG[2])])
    bend_k = np.array([BEND[0], BEND[1], BEND[2]])
    dep_fi, dep_x, dep_y = [], [], []
    ends = {"lift": 0, "out": 0, "uphill": 0, "stall": 0, "long": 0}
    for step in range(MAX_STEPS):
        if not len(x):
            break
        rr, cc = g.cell(x, y)
        inb = g.inside(rr, cc)
        ends["out"] += int((~inb).sum())
        if not inb.all():
            keep = inb
            x, y, gx, gy, going, hx, hy, lane, phase, board, zmin, stall, rr, cc = (
                v[keep] for v in (x, y, gx, gy, going, hx, hy, lane, phase, board, zmin, stall, rr, cc))
            if not len(x):
                break
        fi = rr * g.W + cc
        z = F.z[fi]
        zmin = np.minimum(zmin, z)
        k = F.near[fi]; d = F.near_d[fi]
        kind = S["kind"][k]
        tx, ty = S["tx"][k], S["ty"][k]
        # past a run's end (nothing below it to aim for) is off the network
        past = S["end"][k] & ((x - S["x"][k]) * tx + (y - S["y"][k]) * ty > 0)
        on = (d < S["reach"][k]) & ~past
        nx, ny = -ty, tx
        hw, sp = S["hw"][k], S["spread"][k]
        lane_t = np.where(kind == 1, LANE_TRACK * np.clip(np.rint(lane), -1, 1) * hw + LANE_TRACK_JIT * hw * lane, sp * lane)
        bend = S["bend"][k]
        lane_t = lane_t + S["mid"][k] + np.sign(bend) * np.minimum(1.0, np.abs(bend) * BEND_R) * bend_k[kind] * hw
        px = S["x"][k] + nx * lane_t + tx * LOOK - x
        py = S["y"][k] + ny * lane_t + ty * LOOK - y
        dx, dy = unit(px, py)
        fx, fy = F.fall[0, fi], F.fall[1, fi]
        off = (kind == 2) & on
        dx = np.where(off, dx + FALL_W * fx, dx); dy = np.where(off, dy + FALL_W * fy, dy)
        fl = np.hypot(fx, fy)
        dx = np.where(on, dx, np.where(fl > FLAT_FALL, fx, hx)); dy = np.where(on, dy, np.where(fl > FLAT_FALL, fy, hy))
        if F.pull is not None:
            pw = F.pull[2, fi]
            # off the network, or off-piste in an outer lane (past one sigma): the riders in the run keep their lanes
            use = (pw > 0) & (~on | ((kind == 2) & (np.abs(lane) > 1.0)))
            dx = np.where(use, dx * (1 - pw) + F.pull[0, fi], dx); dy = np.where(use, dy * (1 - pw) + F.pull[1, fi], dy)
        # the lift exit: head for the run picked until there
        if going.any():
            ex, ey = gx - x, gy - y
            arrived = going & (np.hypot(ex, ey) < ARRIVE)
            going = going & ~arrived
            ux, uy = unit(ex, ey)
            dx = np.where(going, ux, dx); dy = np.where(going, uy, dy)
        stop = np.zeros(len(x), bool)
        # a lift's bottom station draws the riders who take it
        if F.sink is not None and step >= MIN_RIDE:
            sid, sd = F.sink[0][fi], F.sink[1][fi]
            # a rider takes it by its draw, or when no run goes on from here (and then sticks to it)
            take = (sid >= 0) & (board[np.arange(len(x)), np.maximum(sid, 0)] | ~on) & ~going
            if take.any():
                board[np.nonzero(take)[0], sid[take]] = True
                bx = np.array([b[0] for b in F.bottoms])[np.maximum(sid, 0)]
                by = np.array([b[1] for b in F.bottoms])[np.maximum(sid, 0)]
                ux, uy = unit(bx - x, by - y)
                w = np.where(take, 1 - sd / SINK_R, 0.0)
                dx, dy = dx * (1 - w) + ux * w, dy * (1 - w) + uy * w
                boarded = take & (sd < SINK_STOP)
                ends["lift"] += int(boarded.sum()); stop |= boarded
        dx, dy = unit(dx, dy)
        nh = rng.normal(0, HEAD_NOISE, len(x))
        hx, hy = unit(INERTIA * hx + (1 - INERTIA) * dx, INERTIA * hy + (1 - INERTIA) * dy)
        c, s = np.cos(nh), np.sin(nh)
        hx, hy = hx * c - hy * s, hx * s + hy * c
        # deposit the travel direction, swung by the rider's turns
        kd = np.where(on, kind, 3)
        ang = turn_k[kd] * np.sin(phase)
        c, s = np.cos(ang), np.sin(ang)
        dep_fi.append(fi[~stop]); dep_x.append((hx * c - hy * s)[~stop].astype(np.float32)); dep_y.append((hx * s + hy * c)[~stop].astype(np.float32))
        phase = phase + math.pi * STEP / TURN_L
        x = x + hx * STEP; y = y + hy * STEP
        lane = lane * (1 - a_lane) + math.sqrt(2 * a_lane) * rng.normal(0, 1, len(x))
        up = z > zmin + UPHILL
        ends["uphill"] += int((up & ~stop).sum()); stop |= up
        stall = np.where(~on & (fl < FLAT_FALL), stall + 1, 0)
        st_ = stall > STALL_STEPS
        ends["stall"] += int((st_ & ~stop).sum()); stop |= st_
        if stop.any():
            keep = ~stop
            x, y, gx, gy, going, hx, hy, lane, phase, board, zmin, stall = (
                v[keep] for v in (x, y, gx, gy, going, hx, hy, lane, phase, board, zmin, stall))
    ends["long"] = int(len(x))
    if not dep_fi:
        return None, ends
    fi = np.concatenate(dep_fi); vx = np.concatenate(dep_x); vy = np.concatenate(dep_y)
    return (fi, vx, vy, np.ones(len(fi), np.float32)), dict(ends, riders=N, steps=len(fi))


def accumulate(F, dep):
    """density (blurred rider steps per cell) and the mean direction vector"""
    from scipy import ndimage
    g = F.g
    n = g.H * g.W
    parts = [dep] + ([F.tl] if F.tl is not None else [])
    fi = np.concatenate([p[0] for p in parts]); w = np.concatenate([p[3] for p in parts]).astype(np.float64)
    vx = np.concatenate([p[1] for p in parts]) * w; vy = np.concatenate([p[2] for p in parts]) * w
    sig = KERNEL / RES
    C = ndimage.gaussian_filter(np.bincount(fi, w, n).reshape(g.H, g.W).astype(np.float32), sig)
    VX = ndimage.gaussian_filter(np.bincount(fi, vx, n).reshape(g.H, g.W).astype(np.float32), sig)
    VY = ndimage.gaussian_filter(np.bincount(fi, vy, n).reshape(g.H, g.W).astype(np.float32), sig)
    return C, VX, VY


def encode(C, VX, VY):
    """the RGB bytes: direction vector and density (see the module doc)"""
    ridden = C[C > RIDDEN_C]
    ref = float(np.percentile(ridden, DENSITY_PCT)) if len(ridden) else 1.0
    den = 1 - np.exp(-np.sqrt(np.maximum(C, 0) / max(ref, 1e-6)))
    B = np.rint(den * 255).astype(np.uint8)
    mx = VX / np.maximum(C, 1e-9); my = VY / np.maximum(C, 1e-9)
    L = np.hypot(mx, my); f = np.where(L > 1, 1 / np.maximum(L, 1e-9), 1.0)
    mx, my = mx * f, my * f
    R = np.rint((mx * 0.5 + 0.5) * 255).astype(np.uint8)
    G = np.rint((my * 0.5 + 0.5) * 255).astype(np.uint8)
    none = B == 0
    R[none] = 128; G[none] = 128
    return np.stack([R, G, B], -1), ref


def decode(rgb):
    """(direction x, direction y, density 0..1) from the bytes"""
    a = rgb.astype(np.float32) / 255
    return a[..., 0] * 2 - 1, a[..., 1] * 2 - 1, a[..., 2]


def write_tiles(pack_dir, g, rgb):
    tx_n, ty_n = int(math.ceil(g.W / TILE)), int(math.ceil(g.H / TILE))
    padded = np.zeros((ty_n * TILE, tx_n * TILE, 3), np.uint8)
    padded[..., 0] = 128; padded[..., 1] = 128
    padded[ty_n * TILE - g.H:, :g.W] = rgb
    d = os.path.join(pack_dir, KIND)
    if os.path.isdir(d):
        for f in os.listdir(d):
            os.remove(os.path.join(d, f))
    os.makedirs(d, exist_ok=True)
    size = 0
    for ty in range(ty_n):
        for tx in range(tx_n):
            r0 = (ty_n - 1 - ty) * TILE
            p = os.path.join(d, f"{tx}_{ty}.png")
            Image.fromarray(padded[r0:r0 + TILE, tx * TILE:(tx + 1) * TILE], "RGB").save(p, optimize=True)
            size += os.path.getsize(p)
    return {"res": RES, "tileSize": TILE, "minX": g.x0, "minY": g.y0, "tilesX": tx_n, "tilesY": ty_n}, size


def build_traffic(pack_dir, meta, features=None, log=print):
    """write traffic/ and return the meta entry (None when the pack has no runs to ride)"""
    t0 = time.time()
    if features is None:
        features = json.load(open(os.path.join(pack_dir, "features.json"), encoding="utf-8"))
    if "mask" not in meta or "bounds" not in meta:
        log("  traffic: no mask grid, none")
        return None
    F = Field(pack_dir, meta, features, log=log)
    t1 = time.time()
    dep, info = simulate(F)
    if dep is None:
        log("  traffic: no runs, none")
        d = os.path.join(pack_dir, KIND)
        if os.path.isdir(d):
            for f in os.listdir(d):
                os.remove(os.path.join(d, f))
            os.rmdir(d)
        return None
    t2 = time.time()
    C, VX, VY = accumulate(F, dep)
    rgb, ref = encode(C, VX, VY)
    entry, size = write_tiles(pack_dir, F.g, rgb)
    ridden = (rgb[..., 2] > 0).mean()
    log(f"  traffic: {info['riders']} riders over {F.lines} runs ({F.kinds} km groomer / track / off-piste line), "
        f"{info['steps']} steps, ends {dict((k, v) for k, v in info.items() if k not in ('riders', 'steps'))}; "
        f"{'%d tree line samples' % len(F.tl[0]) if F.tl is not None else 'no tree lines'}; "
        f"density ref {ref:.2f}, {ridden * 100:.1f}% of cells ridden; {entry['tilesX']} x {entry['tilesY']} tiles, "
        f"{size / 1e6:.2f} MB; {t1 - t0:.1f} s field, {t2 - t1:.1f} s riders, {time.time() - t2:.1f} s write")
    return entry


def read_traffic(pack_dir, meta):
    """the traffic tiles back on the grid (H, W, 3), row 0 = north, cropped to the bounds like the writer"""
    t = meta[KIND]; g = Grid(meta)
    n = t["tileSize"]
    out = np.zeros((t["tilesY"] * n, t["tilesX"] * n, 3), np.uint8)
    for ty in range(t["tilesY"]):
        for tx in range(t["tilesX"]):
            r0 = (t["tilesY"] - 1 - ty) * n
            out[r0:r0 + n, tx * n:(tx + 1) * n] = np.asarray(Image.open(os.path.join(pack_dir, KIND, f"{tx}_{ty}.png")).convert("RGB"))
    return out[out.shape[0] - g.H:, :g.W], g


def view(pack_dir, box, path, scale=2, arrow=24.0):
    """a top-down picture of the map over the hillshade: density as colour, the mean direction as ticks every `arrow`
    m (from a dot, as long as its coherence), the run lines thin and white"""
    from PIL import ImageDraw
    meta = json.load(open(os.path.join(pack_dir, "meta.json"), encoding="utf-8"))
    rgb, g = read_traffic(pack_dir, meta)
    x0, y0, x1, y1 = box
    c0, c1 = int((x0 - g.x0) / RES), int(math.ceil((x1 - g.x0) / RES))
    r0, r1 = int((g.yT - y1) / RES), int(math.ceil((g.yT - y0) / RES))
    z = read_heights(pack_dir, meta, g)[r0:r1, c0:c1].astype(np.float64)
    gy_, gx_ = np.gradient(np.nan_to_num(z, nan=np.nanmean(z)), RES)
    # sun from the north-west, 40 degrees up
    nz = 1 / np.sqrt(1 + gx_ ** 2 + gy_ ** 2)
    shade = np.clip(nz * (math.sin(math.radians(40)) + math.cos(math.radians(40)) * (gx_ * -0.707 + gy_ * -0.707)), 0, 1)
    base = (0.35 + 0.65 * shade)[..., None] * np.array([225, 230, 240])
    vx, vy, den = decode(rgb[r0:r1, c0:c1].astype(np.float32))
    # density: transparent blue to orange to red
    stops = np.array([[40, 90, 220], [250, 170, 40], [230, 30, 30]], np.float64)
    t = np.clip(den, 0, 1)[..., None]
    col = np.where(t < 0.5, stops[0] + (stops[1] - stops[0]) * (t / 0.5), stops[1] + (stops[2] - stops[1]) * ((t - 0.5) / 0.5))
    a = np.clip(den * 1.6, 0, 0.85)[..., None]
    img = (base * (1 - a) + col * a).clip(0, 255).astype(np.uint8)
    im = Image.fromarray(img).resize((img.shape[1] * scale, img.shape[0] * scale), Image.NEAREST)
    d = ImageDraw.Draw(im)
    px = lambda x, y: ((x - (g.x0 + c0 * RES)) / RES * scale, ((g.yT - r0 * RES) - y) / RES * scale)
    for r in json.load(open(os.path.join(pack_dir, "features.json"), encoding="utf-8")).get("runs", []):
        pts = [px(q[0], q[1]) for q in r["points"]]
        if len(pts) > 1:
            d.line(pts, fill=(255, 255, 255), width=1)
    step = int(round(arrow / RES))
    L = arrow * 0.8 / RES * scale
    for rr in range(step // 2, r1 - r0, step):
        for cc in range(step // 2, c1 - c0, step):
            if den[rr, cc] < 0.04:
                continue
            ux, uy = float(vx[rr, cc]), float(vy[rr, cc])
            ax, ay = (cc + 0.5) * scale, (rr + 0.5) * scale
            d.line([(ax, ay), (ax + ux * L, ay - uy * L)], fill=(20, 20, 20), width=2)
            d.ellipse([ax - 2, ay - 2, ax + 2, ay + 2], fill=(20, 20, 20))
    im.save(path, optimize=True)
    return path


def main(argv):
    if not argv or argv[0].startswith("-"):
        sys.exit(__doc__)
    pack_dir = argv[0]
    if "--view" in argv:
        i = argv.index("--view")
        print(view(pack_dir, [float(v) for v in argv[i + 1].split(",")], argv[i + 2]))
        return
    mp = os.path.join(pack_dir, "meta.json")
    meta = json.load(open(mp, encoding="utf-8"))
    e = build_traffic(pack_dir, meta)
    if e:
        meta[KIND] = e
    else:
        meta.pop(KIND, None)
    from packwriter import write_meta
    write_meta(pack_dir, meta)


if __name__ == "__main__":
    main(sys.argv[1:])
