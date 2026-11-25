#!/usr/bin/env python3
"""Glade tree lines from the terrain (FEAT-334): the worn lines riders cut down through the trees beside the black and
gladed runs, traced on a cost field over the pack's own ground and trunks, for the game's trenches, moguls and trim
(SnowboardAnywhere FEAT-333, game/src/pack/treeLines.ts).

python pipeline/tree_lines.py packs/<slug> [--only <run name>]
python pipeline/tree_lines.py packs/<slug> --straightness [<run name>]

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
  4. Riders (FEAT-378). Seeds every SEED_GAP m (Poisson disk, SEED_GAP_TREES beside a tree run) in a band
     OFF_MIN..OFF_MAX m off the run on both sides, over its upper SEED_SPAN, plus ENTRY_LINES entrances across a tree
     run's top edge (ENTRY_OFF + ENTRY_DOFF i m out). Highest first, each rider rides the field's route out (its course:
     where the cheapest way out goes COURSE_M m ahead) DS m a step, in linked turns of ARC_R m (tighter where the trees
     are TIGHT), and controls its speed by how far across the hill each turn finishes: FINISH_DEG by the pitch, nearly
     straight with gentle wiggles on the gentle and well across on the steep, held HOLD_M m. It plans each turn LOOK_M m
     ahead through the gaps between the detected trunks: the next turn as usual, shorter, harder or tighter, the same way
     again or a quick dodge round a trunk, a straight shot down a clear gap then a hard finish (on the steep, SHOT_*), a
     traverse across or slightly up the hill (TRAVERSE_*, more in tight trees, and the way round where no turn gets
     through), each costed by how near it passes the trunks; a run-up to a flat ahead (RUNUP_*) straightens it. Where no
     plan gets through it takes a few of the field's own steps. In the trees no lane runs straight past STRAIGHT_MAX m
     (a run-up excepted): a weave round a trunk ahead breaks it (`weave`, the biggest crown first, on the side nearest
     the fall line), now and then with a second rider forking round the other side where both ways are good lines
     (FORK_P, FORK_MAX_OFF). The line keeps a conifer's crown
     radius from its trunk (the tree well, WELL_SPECIES). It rides until it gets out, stalls or meets a line already
     ridden below it (within JOIN cells): then it joins it, and that line carries one more rider from there down. So
     lines merge in gullies and funnel at flats by themselves, and the busy ones are the deep ones.
  5. Smooth. Resampled every STEP m, smoothed lightly (SMOOTH_PASSES) with the ends held, curvature clamped to R_MIN
     (the tightest turn the game's trench draws), then the corridor checked
     against the trunks: squeezed to SQUEEZE_HW past one closer than its rim, broken for a step (ramped over RAMP_STEPS)
     where even that hits. Stretches more than OPEN_D m from any trunk are left out (no forest, nothing to wear; the
     game gates by its cover levels too). Each point carries its half-width and strength (riders: STR_LO at one rider
     up to 1 at STR_RIDERS or more), fading in at a seed and out at an exit.
  6. Validate. No trunk inside a corridor; stall stretches (flatter than STALL_TAN for over STALL_M m) counted; the
     spacing between neighbouring lines in the glades; how straight they run (`straightness.py`). Logged, and kept in meta
     `treeLines.checks`. --straightness reports it on a pack's lines as they are, round one run.
Pure: the same pack gives the same lines.

treeLines.json: {"version": 1, "step": STEP, "lines": [{"p": [x, y, half-width, strength, ...], "open": m}, ...]}, pack
metres (x east, y north); `open` (optional) is how many metres from a line's start the game's forest gate does not
apply (an entrance leaving the cat track).
"""
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from straightness import FALL_DEG, TREES_D, off_chord, straightness  # noqa: E402
from pack_geom import Heights, along, h01, run_line, seg_dist, smooth  # noqa: E402,F401

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
JOIN = 1             # cells: a rider this close to a ridden line joins it, on a steep pitch
JOIN_FLAT = 4        # cells: on the flats (under STALL_TAN, from JOIN at FUNNEL_TAN): nobody breaks trail where they bog down
FUNNEL_TAN = 0.36
JOIN_CLIMB = 0.5     # m: a ridden line's point higher than the rider by more than this is not joined onto
JOIN_SPAN = 12       # points either side of where a rider meets a ridden line that it may join onto
MAX_LEN = 5000.0     # m: the longest ride
MIN_LEN = 30.0       # m: a shorter line is left out (its rider still counts on the line it joined)
STEP = 3.0           # m between exported points
SMOOTH_PASSES = 2
# FEAT-378: the rider (`ride`). It rides the field's route out (the course: where the cheapest way out goes COURSE_M m
# ahead) in linked turns, and holds its speed by how far across the hill each turn finishes.
DS = 1.0             # m: the rider's step
COURSE_M = 24.0      # m
TURN_SMOOTH = 6.0    # m: the ground's smoothing for the pitch a turn reads
# the turn's finish angle off the course (degrees) by the pitch (degrees): nearly straight with gentle wiggles under 15,
# well across the hill on the steep; the midpoint (25 degrees of pitch) finishes 50 off. No source gives these (a tuning
# choice): from 15 degrees up they hold the pitch's pull along the finish, tan(pitch) cos(finish), at about 0.25 to 0.3,
# near a skidded turn's drag, so the rider stops gaining speed at each finish.
FINISH_DEG = ((0.0, 8.0), (10.0, 16.0), (15.0, 24.0), (20.0, 36.0), (25.0, 50.0), (30.0, 62.0), (35.0, 70.0), (45.0, 78.0))
FINISH_JITTER = 0.15 # a turn's finish varies by up to this share, rider to rider and turn to turn
FINISH_MAX = 88.0    # degrees: the hardest finish
ARC_R = (4.0, 8.0)   # m: the turn's radius in tight trees and in open ones (never under R_MIN)
R_MIN = 4.0          # m: the tightest turn the game's trench draws: past the rim of a full-width corridor (HW_NEAR
                     # times 1 + WIDTH_VAR, plus TRENCH_WALL, 3.3 m) the inside of a tighter turn would be all trench
HOLD_M = (1.5, 9.0)  # m held across the hill at a turn's finish, on the steep and the gentle
HOLD_PITCH = (15.0, 30.0)   # degrees: gentle under the first, steep from the second
TIGHT = (15.0, 70.0) # detected trunks per ha (smoothed over TIGHT_SIGMA m): open to tight trees
TIGHT_SIGMA = 12.0
LOOK_M = 24.0        # m: each turn is planned this far ahead (two or three gaps)
LOOK_SURE = 8.0      # m past the turn that must be clear; a plan blocked further on costs BLOCKED_COST more
BLOCKED_COST = 1.5
CLEAR_K = 6.0        # a plan's cost for its share of metres nearer than CLEAR to a trunk (through the middle of the gaps)
DEV_K = 1.5          # a plan's cost for a finish off the pitch's, per unit share
PROG_K = 0.2         # a plan's credit per unit of the field's cost it gets out by, per metre ridden
DODGE_DEG, DODGE_HOLD, DODGE_COST = 35.0, 2.0, 1.0   # a quick turn this far off the course round a trunk ahead
RHYTHM_COST = 1.0    # a turn the same way as the last (out of rhythm, round a trunk)
PLAN_NOISE = 0.4     # a rider's whim on each plan's cost
# straight shots: steeper than SHOT_PITCH a gap clear by SHOT_CLEAR m along SHOT_M m is shot straight SHOT_P of the
# turns, then a hard finish SHOT_FINISH degrees past the usual
SHOT_PITCH, SHOT_M, SHOT_P, SHOT_CLEAR, SHOT_FINISH = 22.0, (6.0, 14.0), 0.3, 3.0, 15.0
# run-ups: the course's ground over the next RUNUP_M m flatter than RUNUP_DEG[0] is pointed straight, as usual from RUNUP_DEG[1]
# (its finish cut to RUNUP_KEEP of the usual)
RUNUP_M, RUNUP_DEG, RUNUP_KEEP = 36.0, (7.0, 11.0), 0.15
# traverses: TRAVERSE_P of the turns (open trees, tight ones) cross the hill TRAVERSE_DEG off the course (past 90 is
# slightly up) for TRAVERSE_M m to reach the next opening
TRAVERSE_P, TRAVERSE_DEG, TRAVERSE_M = (0.02, 0.08), (80.0, 98.0), (8.0, 20.0)
# the way round where no turn gets through: a shorter, downhill traverse, TRAVERSE_ROUND of TRAVERSE_M at ROUND_DEG off
TRAVERSE_ROUND, ROUND_DEG = 0.5, (60.0, 78.0)
TRAVERSE_COST = 4.0  # a traverse's cost when the rider isn't after one (it takes it only where no turn goes well)
CLIMB_M = 0.8        # m: the most a rider climbs above the lowest it has been (a traverse slightly up)
WALL_M = 1.0         # m: the rider keeps this far off a run's wall
STALL_RIDE = 60.0    # m ridden without getting nearer the way out: the rider has stalled
# tree wells (Sun Peaks glade safety): the rider's line keeps a conifer's crown radius from its trunk (BLOCK at least),
# read from the nearest WELL_K trunks; spruce, subalpine fir, Douglas-fir, hemlock
WELL_SPECIES, WELL_K = (0, 3, 5, 9), 4
# FEAT-378 v2 (Drew: "you don't get to just point downhill and go in a glade run"): in the trees (TREES_D) a lane never
# runs straight (within STRAIGHT_TOL of its chord) for more than STRAIGHT_MAX m (by pitch STRAIGHT_PITCH degrees: long on
# the gentle, short on the steep; each rider's own +- STRAIGHT_JITTER); then an S-turn pair breaks it (`weave`)
STRAIGHT_MAX, STRAIGHT_PITCH, STRAIGHT_JITTER = (40.0, 18.0), (10.0, 30.0), 0.25
WEAVE_TOL = 2.5      # m: the rider's own track this near its chord counts as a lane (its gentle wiggles smooth out
                     # under STRAIGHT_TOL in the exported line)
WEAVE_AHEAD = (4.0, 16.0)   # m ahead the trunk an S goes round may stand
WEAVE_LAT = 4.0      # m: and this far either side of the path
WEAVE_CENTRE = 1.0   # m: a trunk nearer the path than this stands dead ahead (the S goes the other way from the last)
WEAVE_DEG = (35.0, 50.0)    # off the course, out round the trunk and back across below it
WEAVE_BACK = 4.0     # m held after the turn back across
WEAVE_COST = -3.0    # an S's cost against the usual turn (it wins wherever it gets through)
WEAVE_FREE_P, WEAVE_FREE_DEG = 0.25, 25.0   # no trunk to go round: a gentler S, this share of the time
# forks: FORK_P of the S-turns round a trunk dead ahead send a second rider round its other side, rejoining below (no
# source gives how often; kept occasional); it joins no line for its first FORK_FREE m
FORK_P, FORK_FREE = 0.25, 12.0
FORK_MAX_OFF = 60.0  # degrees: a fork only where both ways round go no further than this off the fall line
WEAVES = ("s-tree", "s-centre", "s-free")   # the weaves' kinds
# v3 (Drew: riders take the side that keeps them nearer the fall line): a weave costs WEAVE_OFF_K per radian its swings
# go off the fall line; going the same way as the last weave costs WEAVE_ALT_COST (a tie-breaker)
WEAVE_OFF_K, WEAVE_ALT_COST = 2.0, 0.1
STR_LO, STR_RIDERS = 0.6, 4
HW_NEAR, HW_FAR = 1.7, 0.9
WIDTH_VAR, WIDTH_L = 0.3, 25.0
FADE_IN, FADE_OUT = 12.0, 30.0
TRENCH_WALL, SQUEEZE_HW, RAMP_STEPS = 1.1, 0.5, 3   # as game/src/pack/treeLines.ts (TRENCH_WALL, SQUEEZE_HW, RAMP_STEPS)
OPEN_D = 30.0        # m from any trunk: no forest
STALL_M = 30.0
SPACING_BAND = (3.0, 10.0)

# FEAT-389 prototype: the rough traffic (traffic.density, no tree lines) as an input. SBA_TL_TRAFFIC "seed" keeps a seed
# candidate with a chance from how busy its side of the run is (TR_FLOOR at none, 1 at the run's busiest), "cost" makes
# a move cheaper where riders already go (1 / (1 + TR_COST_K density)), "both" does both; unset reads no traffic.
TR_MODE = os.environ.get("SBA_TL_TRAFFIC", "")
TR_FLOOR = float(os.environ.get("SBA_TL_TR_FLOOR", "0.15"))
TR_COST_K = float(os.environ.get("SBA_TL_TR_COST", "1.5"))
TR_EDGE = (0.0, 6.0, 12.0, 18.0)   # m off the centreline: where a seed's side of the run is read
DIRS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def eligible(r):
    return bool(r.get("gladed") or (r.get("difficulty") in LINE_DIFF))


class Planner:
    def __init__(self, pack_dir, meta, features, log=print, traffic=None):
        from scipy.spatial import cKDTree
        self.traffic = traffic if TR_MODE else None   # (density 0..1, traffic.Grid)
        import cover
        self.log = log
        self.meta, self.runs = meta, features.get("runs", [])
        self.hts = Heights(pack_dir, meta)
        tr = list(cover.tree_records(pack_dir, meta))
        self.trunks = np.concatenate([t[:, :2] for t in tr]).astype(np.float64) if tr else np.zeros((0, 2))
        self.crowns = np.concatenate([t[:, 4] for t in tr]).astype(np.float64) if tr else np.zeros(0)   # crown radius, m
        sp = np.concatenate([t[:, 5] for t in tr]).astype(np.int64) if tr else np.zeros(0, np.int64)
        # the tree well a rider keeps out of: a conifer's crown radius (low boughs, the well under them), past BLOCK
        self.wells = np.where(np.isin(sp, WELL_SPECIES), np.maximum(self.crowns - BLOCK, 0), 0.0)
        self.kd = cKDTree(self.trunks) if len(self.trunks) else None
        b = meta["bounds"]
        self.gx0, self.gy1 = float(b["minX"]), float(b["maxY"])
        self.kinds = {}     # metres ridden by each kind of plan (turn, shot, traverse, s-tree, s-free, field), for the log
        self.s_turns = {}   # weaves ridden (WEAVES): round a trunk beside the path (s-tree) or dead ahead (s-centre), with
                            # none (s-free); the forks round a trunk dead ahead and those the gate left out (fork-gated);
                            # the weaves that went the other side from the v2 rule (side-changed)
        self.weave_off = [0.0, 0.0]   # metres of weave, and of those more than FORK_MAX_OFF off the fall line
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
        """the distance from each cell to the nearest trunk, m (FEAT-378 v2: less a conifer's well, `wells`)"""
        xs = x0 + (np.arange(w) + 0.5) * RES; ys = y1 - (np.arange(h) + 0.5) * RES
        X, Y = np.meshgrid(xs, ys)
        if self.kd is None:
            return np.full((h, w), np.inf)
        d, _ = self.kd.query(np.column_stack([X.ravel(), Y.ravel()]), distance_upper_bound=OPEN_D + 5)
        dist = d.reshape(h, w)
        if self.wells.max() > 0:
            # a conifer's well counts as nearer: the clearance from the nearest few trunks, less each one's well
            near = np.nonzero((dist <= BLOCK + self.wells.max() + RES).ravel())[0]
            X = np.column_stack([x0 + (near % w + 0.5) * RES, y1 - (near // w + 0.5) * RES])
            d, k = self.kd.query(X, k=WELL_K, distance_upper_bound=BLOCK + self.wells.max() + RES)
            wl = np.concatenate([self.wells, [0.0]])[np.minimum(k, len(self.wells))]
            flat = dist.ravel().copy()
            flat[near] = np.minimum(flat[near], np.min(np.where(np.isfinite(d), d - wl, np.inf), axis=1))
            dist = flat.reshape(h, w)
        return dist

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

    def traffic_at(self, x, y):
        D, g = self.traffic
        x, y = np.asarray(x, np.float64), np.asarray(y, np.float64)
        rr, cc = g.cell(x, y)
        ok = g.inside(rr, cc)
        out = np.zeros(np.shape(x), np.float32)
        out[ok] = D[rr[ok], cc[ok]]
        return out

    def traffic_window(self, x0, y1, w, h):
        xs = x0 + (np.arange(w) + 0.5) * RES; ys = y1 - (np.arange(h) + 0.5) * RES
        X, Y = np.meshgrid(xs, ys)
        return self.traffic_at(X, Y)

    def field(self, z, dist, walls, exits, tr=None):
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
        if tr is not None:
            tree = tree / (1 + TR_COST_K * tr)
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
        cand, edge = [], []
        n = int(SEEDS_MAX * 20)
        for _ in range(n):
            q = rng.uniform(0, s[-1] * SEED_SPAN)
            u = rng.uniform()
            off = OFF_MIN + (OFF_MAX - OFF_MIN) * u * u   # most near the run's edge
            side = 1 if rng.uniform() < 0.5 else -1
            x, y, tx, ty = along(p, s, q)
            cand.append((x - ty * off * side, y + tx * off * side, 0.0))
            if self.traffic is not None and TR_MODE in ("seed", "both"):
                edge.append([(x - ty * e * side, y + tx * e * side) for e in TR_EDGE])
        if edge:
            e = np.asarray(edge)
            busy = self.traffic_at(e[..., 0], e[..., 1]).max(axis=1)
            wt = TR_FLOOR + (1 - TR_FLOOR) * busy / max(float(busy.max()), 1e-6)
            u = np.random.default_rng((int(r.get("osmId") or ri) * 389) & 0x7FFFFFFF).uniform(size=len(cand))
            cand = [c for c, k in zip(cand, u < wt) if k]
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

    def rider_fields(self, T, z, dist, walls, exits, x0, y1):
        """what the rider reads on its way down, flat lists by cell (row-major): the course (unit vector toward where the
        cheapest way out goes COURSE_M m ahead), the pitch (tan, over TURN_SMOOTH m), the pitch ahead along the course
        over RUNUP_M m, the trees' tightness (0..1), the clearance (to a trunk, or WALL_M m less than BLOCK to a run's
        wall), the exits, each cell's cheapest next step"""
        from scipy import ndimage
        h, w = T.shape
        n = h * w
        Tf = T.ravel()
        idx = np.arange(n)
        # each cell's cheapest next step down the field (itself at an exit or where none goes down)
        best, nxt = np.full(n, np.inf), idx.copy()
        for (di, dj), c in self.cost.items():
            r, cc = idx // w + di, idx % w + dj
            inb = (r >= 0) & (r < h) & (cc >= 0) & (cc < w)
            j = np.where(inb, r * w + cc, 0)
            v = np.where(inb, Tf[j] + c.ravel(), np.inf)
            take = (v < best) & inb & (Tf[j] < Tf)
            best[take] = v[take]; nxt[take] = j[take]
        zf = np.where(np.isfinite(z), z, np.nanmax(z) if np.isfinite(z).any() else 0).astype(np.float64)
        zs = ndimage.gaussian_filter(zf, TURN_SMOOTH / RES, mode="nearest")
        gr, gc = np.gradient(zs, RES)
        g = np.hypot(gr, gc).ravel()
        cur, acc, ahead = idx, np.zeros(n), idx
        k_run, k_course = int(round(RUNUP_M / RES)), int(round(COURSE_M / RES))
        for k in range(max(k_run, k_course)):
            cur = nxt[cur]
            if k < k_run:
                acc += g[cur]
            if k == k_course - 1:
                ahead = cur
        cx = (ahead % w - idx % w).astype(np.float64).reshape(h, w)
        cy = -(ahead // w - idx // w).astype(np.float64).reshape(h, w)
        # where the route goes nowhere (an exit, a stall) the course is the fall line
        none = (cx == 0) & (cy == 0)
        cx[none] = -gc[none]; cy[none] = gr[none]
        L = np.maximum(np.hypot(cx, cy), 1e-9)
        cx, cy = ndimage.gaussian_filter(cx / L, 1.0), ndimage.gaussian_filter(cy / L, 1.0)
        L = np.maximum(np.hypot(cx, cy), 1e-9)
        trees = (dist <= TREES_D).ravel().tolist()
        if walls.any():
            dist = np.minimum(dist, ndimage.distance_transform_edt(~walls) * RES - RES / 2 + BLOCK - WALL_M)
        dens = np.zeros((h, w))
        if len(self.trunks):
            c = np.floor((self.trunks[:, 0] - x0) / RES).astype(np.int64); r = np.floor((y1 - self.trunks[:, 1]) / RES).astype(np.int64)
            ins = (c >= 0) & (c < w) & (r >= 0) & (r < h)
            np.add.at(dens, (r[ins], c[ins]), 1e4 / (RES * RES))
            dens = ndimage.gaussian_filter(dens, TIGHT_SIGMA / RES)
        self.rf = {"w": w, "h": h, "x0": x0, "y1": y1, "T": Tf.tolist(), "cx": (cx / L).ravel().tolist(),
                   "cy": (cy / L).ravel().tolist(), "pitch": g.tolist(), "ahead": (acc / max(k_run, 1)).tolist(),
                   "tight": smooth(*TIGHT, dens).ravel().tolist(), "dist": np.minimum(dist, OPEN_D).ravel().tolist(),
                   "exit": exits.ravel().tolist(), "nxt": nxt.tolist(), "join": self.join_r.ravel().tolist(),
                   "z": zs.ravel().tolist(), "fall": np.arctan2(gr, -gc).ravel().tolist(), "trees": trees}

    def probe(self, x, y):
        """the cell under (x, y) (-1 outside the window), and the ground and the clearance there, bilinear between cell
        centres"""
        f = self.rf
        w, h = f["w"], f["h"]
        fc, fr = (x - f["x0"]) / RES, (f["y1"] - y) / RES
        if not (0 <= fc < w and 0 <= fr < h):
            return -1, 0.0, 0.0
        i = int(fr) * w + int(fc)
        fc -= 0.5; fr -= 0.5
        c, r = int(fc) if fc > 0 else 0, int(fr) if fr > 0 else 0
        c, r = min(c, w - 2), min(r, h - 2)
        u, v = min(1.0, max(0.0, fc - c)), min(1.0, max(0.0, fr - r))
        j = r * w + c
        a, b, cc, d = (1 - u) * (1 - v), u * (1 - v), (1 - u) * v, u * v
        z, dist = f["z"], f["dist"]
        return (i, z[j] * a + z[j + 1] * b + z[j + w] * cc + z[j + w + 1] * d,
                dist[j] * a + dist[j + 1] * b + dist[j + w] * cc + dist[j + w + 1] * d)

    def sim(self, x, y, hd, segs, look, clear_min=BLOCK, ztop=math.inf, n_first=1):
        """ride `segs` from (x, y) heading `hd` (radians from east), DS m a step, for `look` m or to an exit. Each segment
        (angle off the course, radius, metres held) turns toward the course plus its angle no tighter than its radius,
        then holds that heading off the course for its metres. Returns the points, the heading at each, how many points
        the first `n_first` segments rode (None if it didn't get that far), the cost of passing near trunks, the field's cost at
        the last point, and whether it got through to the end (no trunk nearer than `clear_min`, nothing off the field,
        nothing higher than `ztop`); when it didn't, the points stop short."""
        f = self.rf
        T, cxl, cyl, ex, fall, pitch = f["T"], f["cx"], f["cy"], f["exit"], f["fall"], f["pitch"]
        pts, hds, near, first, L = [], [], 0.0, None, 0.0
        i = self.probe(x, y)[0]
        t_last = T[i]
        for k, (rel, rad, hold) in enumerate(segs):
            held, turning, lim = 0.0, True, DS / rad
            most = max(math.radians(FINISH_MAX), abs(rel))
            while L < look:
                want = math.atan2(cyl[i], cxl[i]) + rel
                if pitch[i] > ANGLE_LO:
                    # never further round than the finish (or the traverse) off the fall line: no turning back up the hill
                    off = (want - fall[i] + math.pi) % (2 * math.pi) - math.pi
                    want = fall[i] + max(-most, min(most, off))
                dif = (want - hd + math.pi) % (2 * math.pi) - math.pi
                if turning and abs(dif) <= lim:
                    turning = False
                if turning:
                    hd += lim if dif > 0 else -lim
                else:
                    hd += max(-lim, min(lim, dif))
                    held += DS
                x += DS * math.cos(hd); y += DS * math.sin(hd); L += DS
                i, z, d = self.probe(x, y)
                if i < 0 or T[i] == math.inf or z > ztop or d < clear_min:
                    return pts, hds, first, near, t_last, False
                t_last = T[i]
                if d < CLEAR:
                    t = (d - BLOCK) / (CLEAR - BLOCK)
                    near += 1 - t * t * (3 - 2 * t)
                pts.append((x, y)); hds.append(hd)
                if ex[i]:
                    return pts, hds, first or len(pts), near, T[i], True
                if not turning and held >= hold:
                    break
            if first is None and k == n_first - 1:
                first = len(pts)
            if L >= look:
                break
        return pts, hds, first, near, T[i], True

    def finish(self, pitch_tan, ahead_tan):
        """the finish angle off the course for this pitch (radians), straightened for a run-up to a flat ahead"""
        phi = float(np.interp(math.degrees(math.atan(pitch_tan)), [k for k, _ in FINISH_DEG], [v for _, v in FINISH_DEG]))
        return math.radians(phi) * (RUNUP_KEEP + (1 - RUNUP_KEEP) * self.runup(ahead_tan))

    def runup(self, ahead_tan):
        """0 where the ground ahead along the course runs out flat (point it), 1 where it keeps its pitch"""
        return float(smooth(math.tan(math.radians(RUNUP_DEG[0])), math.tan(math.radians(RUNUP_DEG[1])), ahead_tan))

    def plans(self, i, side, rng):
        """the rider's choices for its next turn from cell i, having finished on `side`: (kind, segments it rides,
        segments it looks ahead with, bias, the clearance it needs). The next linked turn as usual, shorter, harder,
        tighter; the same way again; a quick dodge either way (on the gentle); a straight shot through a clear gap then a
        hard finish (on the steep, sometimes); a traverse either way (favoured now and then, more in tight trees, else a
        shorter one down and round where no turn gets through)."""
        f = self.rf
        pitch, tight = f["pitch"][i], f["tight"][i]
        phi0 = self.finish(pitch, f["ahead"][i])
        r0 = ARC_R[1] + (ARC_R[0] - ARC_R[1]) * tight
        hold0 = HOLD_M[1] + (HOLD_M[0] - HOLD_M[1]) * float(smooth(*np.tan(np.radians(HOLD_PITCH)), pitch))
        nxt = -side
        back = [(side * phi0, r0, hold0), (nxt * phi0, r0, hold0)]
        out = []
        for fk, rk in ((1.0, r0), (0.7, r0), (1.3, r0), (1.0, ARC_R[0]), (0.5, ARC_R[0])):
            phi = min(math.radians(FINISH_MAX), phi0 * fk * (1 + FINISH_JITTER * (2 * rng.uniform() - 1)))
            out.append(("turn", [(nxt * phi, max(R_MIN, rk), hold0)], back, DEV_K * abs(fk - 1), BLOCK))
        # the same way again (a trunk where the next turn would go): out of rhythm, so it costs RHYTHM_COST
        for fk in (1.0, 0.5):
            out.append(("turn", [(side * phi0 * fk, max(R_MIN, ARC_R[0]), hold0)], [back[1], back[0]], RHYTHM_COST + DEV_K * abs(fk - 1), BLOCK))
        # a quick dodge round a trunk ahead, either way, however gentle the pitch
        if phi0 < math.radians(DODGE_DEG):
            for s in (nxt, side):
                out.append(("turn", [(s * math.radians(DODGE_DEG), max(R_MIN, ARC_R[0]), DODGE_HOLD)], back, DODGE_COST, BLOCK))
        if math.degrees(math.atan(pitch)) >= SHOT_PITCH and rng.uniform() < SHOT_P:
            shot = SHOT_M[0] + (SHOT_M[1] - SHOT_M[0]) * rng.uniform()
            hard = min(math.radians(FINISH_MAX), phi0 + math.radians(SHOT_FINISH))
            out.append(("shot", [(0.0, r0, shot), (nxt * hard, max(R_MIN, ARC_R[0]), hold0)], back[:1], -1.0, SHOT_CLEAR))
        fav = rng.uniform() < TRAVERSE_P[0] + (TRAVERSE_P[1] - TRAVERSE_P[0]) * tight
        for s in (1, -1):
            lo, hi = TRAVERSE_DEG if fav else ROUND_DEG
            a = math.radians(lo + (hi - lo) * rng.uniform())
            m = (TRAVERSE_M[0] + (TRAVERSE_M[1] - TRAVERSE_M[0]) * rng.uniform()) * (1 if fav else TRAVERSE_ROUND)
            out.append(("traverse", [(s * a, max(R_MIN, ARC_R[0]), m)], [(-s * phi0, r0, hold0)], -1.0 if fav else TRAVERSE_COST, BLOCK))
        return out

    def weave(self, x, y, hd, i, s_side, rng, force=None):
        """FEAT-378 v2/v3: turns to break a straight lane in the trees, as plans (see `plans`), and an info dict: each
        side's swing off the fall line (radians) and the side the v2 rule took (for the log); None when there are none.
        Round a detected trunk WEAVE_AHEAD m ahead within WEAVE_LAT m of the path, the biggest crown first, on either side
        (`force`: that one only): out WEAVE_DEG off the course until abreast, then a tight turn back across below it (an S)
        or on down that side (one turn). Each costs WEAVE_OFF_K per radian its swings go off the fall line, so the
        downhill side wins where the lane runs across the slope; a swing past FINISH_MAX is no plan, and going the same
        way as the last weave costs WEAVE_ALT_COST (a tie-breaker). With no trunk there, a gentler S, WEAVE_FREE_P of the
        time."""
        f = self.rf
        r0 = max(R_MIN, ARC_R[1] + (ARC_R[0] - ARC_R[1]) * f["tight"][i])
        phi0 = self.finish(f["pitch"][i], f["ahead"][i])
        ux, uy = math.cos(hd), math.sin(hd)
        course, fall, sloped = math.atan2(f["cy"][i], f["cx"][i]), f["fall"][i], f["pitch"][i] > ANGLE_LO

        def off(rel):
            return abs((course + rel - fall + math.pi) % (2 * math.pi) - math.pi) if sloped else 0.0

        best = None
        if self.kd is not None:
            mx, my = x + ux * sum(WEAVE_AHEAD) / 2, y + uy * sum(WEAVE_AHEAD) / 2
            for t in self.kd.query_ball_point((mx, my), (WEAVE_AHEAD[1] - WEAVE_AHEAD[0]) / 2 + WEAVE_LAT):
                dx, dy = self.trunks[t, 0] - x, self.trunks[t, 1] - y
                fwd, lat = dx * ux + dy * uy, dx * uy - dy * ux   # lat > 0: the trunk is to the right
                if WEAVE_AHEAD[0] <= fwd <= WEAVE_AHEAD[1] and abs(lat) <= WEAVE_LAT:
                    score = self.crowns[t] / (1 + abs(lat) / WEAVE_LAT)
                    if best is None or score > best[0]:
                        best = (score, fwd, lat)
        out, lim = [], math.radians(FINISH_MAX)
        if best:
            _, fwd, lat = best
            centre = abs(lat) < WEAVE_CENTRE
            kind, v2 = ("s-centre", -s_side) if centre else ("s-tree", 1 if lat > 0 else -1)
            for s in (force,) if force else (1, -1):
                for a in map(math.radians, WEAVE_DEG):
                    if off(s * a) > lim:
                        continue
                    hold, tie = max(1.0, fwd - r0 * a), WEAVE_ALT_COST * (s == s_side)
                    out.append((kind, [(s * a, r0, hold), (-s * a, max(R_MIN, ARC_R[0]), WEAVE_BACK)], [(s * phi0, r0, HOLD_M[0])],
                                WEAVE_COST + WEAVE_OFF_K * (off(s * a) + off(-s * a)) / 2 + tie, BLOCK))
                    out.append((kind, [(s * a, r0, hold + WEAVE_BACK)], [(-s * phi0, r0, HOLD_M[0])],
                                WEAVE_COST + WEAVE_OFF_K * off(s * a) + tie, BLOCK))
            a = math.radians(WEAVE_DEG[0])
        elif force is None and rng.uniform() < WEAVE_FREE_P:
            kind, v2, a = "s-free", -s_side, math.radians(WEAVE_FREE_DEG)
            for s in (1, -1):
                if off(s * a) <= lim:
                    out.append((kind, [(s * a, r0, WEAVE_BACK), (-s * a, r0, WEAVE_BACK)], [(s * phi0, r0, HOLD_M[0])],
                                WEAVE_COST + WEAVE_OFF_K * (off(s * a) + off(-s * a)) / 2 + WEAVE_ALT_COST * (s == s_side), BLOCK))
        else:
            return out, None
        return out, {"v2": v2, "off": {1: off(a), -1: off(-a)}}

    def ride(self, sx, sy, rng, fork=None):
        """one rider from (sx, sy) down the field in linked turns until it gets out, stalls or meets a ridden line (then
        it joins it). Returns its points every DS m (about) and the (line id, point index) it joined, or None. A `fork`
        (heading, side) starts it on another rider's line, round the trunk ahead on the other side; it joins no line for
        its first FORK_FREE m. It may ask for a fork of its own line (`self.fork`)."""
        self.fork = None
        f = self.rf
        i = self.probe(sx, sy)[0]
        if i < 0 or f["T"][i] == math.inf:
            # the seed sits on a trunk or a wall: the nearest reachable cell within 3 cells
            c, r = int((sx - f["x0"]) / RES), int((f["y1"] - sy) / RES)
            best = None
            for dr in range(-3, 4):
                for dc in range(-3, 4):
                    a, b = r + dr, c + dc
                    if 0 <= a < f["h"] and 0 <= b < f["w"] and f["T"][a * f["w"] + b] < math.inf and (best is None or dr * dr + dc * dc < best[0]):
                        best = (dr * dr + dc * dc, a, b)
            if not best:
                self.why = "stuck"
                return [], None
            sx, sy = f["x0"] + (best[2] + 0.5) * RES, f["y1"] - (best[1] + 0.5) * RES
            i = self.probe(sx, sy)[0]
        x, y = sx, sy
        hd = math.atan2(f["cy"][i], f["cx"][i]) if fork is None else fork[0]
        side = 1 if rng.uniform() < 0.5 else -1
        pts = [(x, y)]
        gc0 = int(round((f["x0"] - self.gx0) / RES)); gr0 = int(round((self.gy1 - f["y1"]) / RES))
        t_best, since, zlow = f["T"][i], 0.0, self.probe(x, y)[1]
        free = FORK_FREE if fork else 0.0
        cap_k, since_s, s_side = 1 + STRAIGHT_JITTER * (2 * rng.uniform() - 1), 0.0, side
        while len(pts) * DS < MAX_LEN:
            i = self.probe(x, y)[0]
            best = None
            info = None
            if fork is None:
                plans = self.plans(i, side, rng)
            else:
                plans, info = self.weave(x, y, hd, i, s_side, rng, fork[1])
            fork_at = fork and (x, y, hd)
            fork = None
            # FEAT-378 v2: no long straight lane in the trees (a run-up to a flat ahead stays straight)
            cap = cap_k * float(np.interp(math.degrees(math.atan(f["pitch"][i])), STRAIGHT_PITCH, STRAIGHT_MAX))
            n = int(cap / DS)
            if (since_s >= cap and len(pts) > n and f["trees"][i] and self.runup(f["ahead"][i]) > 0.5
                    and off_chord(np.asarray(pts[-n:])) <= WEAVE_TOL):
                more, info = self.weave(x, y, hd, i, s_side, rng)
                plans += more
            ok_sides = set()   # the sides a weave round a trunk dead ahead gets through on (for a fork)
            for kind, ex, lk, bias, cmin in plans:
                p, hs, first, near, t_end, ok = self.sim(x, y, hd, ex + lk, LOOK_M + sum(e[2] for e in ex), cmin, zlow + CLIMB_M, len(ex))
                if not first or not (ok or len(p) >= first + LOOK_SURE / DS):
                    continue
                if kind == "s-centre" and ok:
                    ok_sides.add(1 if ex[0][0] > 0 else -1)
                cost = bias + (0 if ok else BLOCKED_COST) + (CLEAR_K * near - PROG_K * (f["T"][i] - t_end)) / len(p) + PLAN_NOISE * rng.standard_normal()
                if best is None or cost < best[0]:
                    best = (cost, kind, p[:first], hs[first - 1], ex[-1][0], ex[0][0])
            if best is None and fork_at:
                self.why = "fork-blocked"   # a fork goes round its side or not at all
                return [], None
            if best is None:
                # no plan gets through: a few of the field's own cheapest steps (round the trunk), then plan again
                cells, j = [], i
                for _ in range(3):
                    j = f["nxt"][j]
                    cells.append((f["x0"] + (j % f["w"] + 0.5) * RES, f["y1"] - (j // f["w"] + 0.5) * RES))
                if j == i:
                    self.why = "stuck"
                    return pts, None
                step = []
                for a, b in zip([(x, y)] + cells[:-1], cells):
                    nn = max(1, int(round(math.hypot(b[0] - a[0], b[1] - a[1]) / DS)))
                    step += [(a[0] + (b[0] - a[0]) * k / nn, a[1] + (b[1] - a[1]) * k / nn) for k in range(1, nn + 1)]
                hd = math.atan2(cells[-1][1] - cells[0][1], cells[-1][0] - cells[0][0]) if len(set(cells)) > 1 else hd
            else:
                _, kind, step, hd, rel, rel0 = best
                went = 1 if rel0 > 0 else -1
                if kind == "s-centre" and not fork_at and not self.fork and rng.uniform() < FORK_P:
                    # a trunk dead ahead: now and then a second rider goes round it the other way (rejoining below)
                    if fork_ok(info, went, ok_sides):
                        self.fork = (x, y, hd, -went)
                    else:
                        self.s_turns["fork-gated"] = self.s_turns.get("fork-gated", 0) + 1
                side = 1 if rel > 0 else -1   # the side the plan finished on
                if kind.startswith("s-"):
                    since_s, s_side = -len(step) * DS, went
                    if info and went != info["v2"]:
                        self.s_turns["side-changed"] = self.s_turns.get("side-changed", 0) + 1
            self.kinds[kind] = self.kinds.get(kind, 0) + len(step) * DS
            if kind.startswith("s-"):
                # how far off the fall line the weaves go, for the log
                for (ax, ay), (bx, by) in zip([(x, y)] + step[:-1], step):
                    k = self.probe(bx, by)[0]
                    if f["pitch"][k] > ANGLE_LO:
                        off = abs((math.atan2(by - ay, bx - ax) - f["fall"][k] + math.pi) % (2 * math.pi) - math.pi)
                        self.weave_off[0] += DS
                        self.weave_off[1] += DS * (off > math.radians(FORK_MAX_OFF))
            since_s += len(step) * DS
            if kind.startswith("s-"):
                self.s_turns[kind] = self.s_turns.get(kind, 0) + 1
            for (px, py) in step:
                j, zp, _ = self.probe(px, py)
                pts.append((px, py))
                jr, c, r = (f["join"][j] if len(pts) * DS > free else -1), j % f["w"], j // f["w"]
                for dr in range(-jr, jr + 1):
                    for dc in range(-jr, jr + 1):
                        if dr * dr + dc * dc <= jr * jr + 1:
                            o = self.occ.get((gc0 + c + dc, gr0 + r + dr))
                            if o is not None:
                                # onto the ridden line's lowest point within reach (not back up it)
                                lid, k = o
                                xy, reach = self.lines[lid]["xy"], (jr + 1.5) * RES
                                near = [q for q in range(max(0, k - JOIN_SPAN), min(len(xy), k + JOIN_SPAN + 1))
                                        if math.hypot(xy[q][0] - px, xy[q][1] - py) <= reach]
                                k = min(near, key=lambda q: (self.probe(*xy[q])[1], -q)) if near else k
                                if self.probe(*xy[k])[1] <= zp + JOIN_CLIMB:
                                    self.why = "join"
                                    return pts, (lid, k)
                                # it lies above: ride on alongside (it joins further down)
                if f["exit"][j]:
                    self.why = "exit"
                    return pts, None
                zlow = min(zlow, zp)
                if f["T"][j] < t_best - 1:
                    t_best, since = f["T"][j], 0.0
                else:
                    since += DS
                    if since > STALL_RIDE:
                        self.why = "stall"
                        return pts, None
            x, y = pts[-1]
        self.why = "long"
        return pts, None

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
            tr = self.traffic_window(x0, y1, w, h) if self.traffic is not None and TR_MODE in ("cost", "both") else None
            T, zs = self.field(z, dist, walls, exits, tr)
            self.rider_fields(T, z, dist, walls & ~exits, exits & np.isfinite(T), x0, y1)
            rng = np.random.default_rng((int(r.get("osmId") or ri) * 7919) & 0x7FFFFFFF)
            sd = self.seeds(ri, r, p, s)
            zsd = []
            for (sx, sy, op) in sd:
                cc, rr = int((sx - x0) / RES), int((y1 - sy) / RES)
                zsd.append(zs[rr, cc] if 0 <= rr < h and 0 <= cc < w else -1e9)
            gc0 = int(round((x0 - self.gx0) / RES)); gr0 = int(round((self.gy1 - y1) / RES))
            n0 = len(self.lines)
            self.whys = {}
            todo = [(sd[k], None) for k in np.argsort(-np.asarray(zsd), kind="stable")][::-1]
            while todo:
                (sx, sy, op), fork = todo.pop()
                xy, join = self.ride(sx, sy, rng, fork)
                if self.fork:
                    self.s_turns["fork"] = self.s_turns.get("fork", 0) + 1
                    todo.append(((self.fork[0], self.fork[1], 0.0), self.fork[2:]))
                if not xy:
                    continue
                if join is not None and len(xy) * DS < MIN_LEN:
                    # a stub onto a ridden line: its rider rides that line, and nobody joins the stub (it is left out)
                    self.add_rider(join)
                    self.whys[self.why] = self.whys.get(self.why, 0) + 1
                    continue
                lid = len(self.lines)
                self.lines.append({"xy": xy, "riders": np.ones(len(xy)), "join": join, "open": op, "run": ri, "exit": join is None})
                if join is not None:
                    self.add_rider(join)
                self.whys[self.why] = self.whys.get(self.why, 0) + 1
                for i, (px, py) in enumerate(xy):
                    self.occ.setdefault((gc0 + int((px - x0) / RES), gr0 + int((y1 - py) / RES)), (lid, i))
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


def fork_ok(info, went, ok_sides):
    """a fork round a trunk dead ahead only where both ways are lines a rider would take: each swing within FORK_MAX_OFF
    of the fall line (`info` from `weave`), and the other way (-went) gets through (`ok_sides`)"""
    gate = math.radians(FORK_MAX_OFF)
    return -went in ok_sides and info["off"][went] <= gate and info["off"][-went] <= gate


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


def build_tree_lines(pack_dir, meta, features=None, only=None, log=print, traffic=None):
    """write treeLines.json and return the meta entry (None when no run gets lines)"""
    if features is None:
        features = json.load(open(os.path.join(pack_dir, "features.json"), encoding="utf-8"))
    if TR_MODE and traffic is None:   # standalone: the rough pass on the pack as it is
        import traffic as _tr
        traffic = _tr.density(pack_dir, meta, features, log=log)
    if TR_MODE:
        log(f"  tree lines read the rough traffic ({TR_MODE}, floor {TR_FLOOR:g}, cost k {TR_COST_K:g})")
    pl = Planner(pack_dir, meta, features, log=log, traffic=traffic)
    pl.plan(only=only)
    lines, st = pl.export()
    if not lines:
        log("  tree lines: none")
        p = os.path.join(pack_dir, FILE)
        if os.path.exists(p):
            os.remove(p)
        return None
    chk = validate(lines, pl)
    sl = straightness(lines, pl.hts, trunks=pl.kd)
    chk["straightness"] = {"sinuosity30": sl["sinuosity30"]["median"], "sinuosity90": sl["sinuosity90"]["median"],
                           "drift60": sl["drift60"]["median"], "fallLine": sl["fallLine"],
                           "straightInTrees": {k: v and v["median"] for k, v in sl["straightInTrees"].items()},
                           "sTurnsPerKm": round(sum(pl.s_turns.get(k, 0) for k in WEAVES) / max(chk["km"], 1e-6), 1),
                           "weaveOffFall": round(pl.weave_off[1] / max(pl.weave_off[0], 1e-6), 3)}
    path = os.path.join(pack_dir, FILE)
    with open(path, "w") as f:
        json.dump({"version": VERSION, "step": STEP, "lines": lines}, f, separators=(",", ":"))
    sp = chk["spacing"] or {}
    log(f"  tree lines: {len(lines)} lines, {chk['km']} km from {len(pl.lines)} riders' traces, {st['squeezed']} squeezes and "
        f"{st['broken']} breaks at a trunk, {chk['trunksInCorridor']} trunks in a corridor, {chk['stalls']} stall stretches "
        f"over {STALL_M:g} m, spacing median {sp.get('median')} m ({(sp.get('inBand') or 0) * 100:.0f}% in "
        f"{SPACING_BAND[0]:g} to {SPACING_BAND[1]:g} m); {os.path.getsize(path) / 1e3:.0f} KB")
    log(f"  tree lines ridden: " + ", ".join(f"{k} {v / 1000:.1f} km" for k, v in sorted(pl.kinds.items())) +
        f"; path over chord {sl['sinuosity30']['median']} over 30 m, {sl['sinuosity90']['median']} over 90 m, drift "
        f"{sl['drift60']['median']} m over 60 m; within {FALL_DEG:g} degrees of the fall line by pitch {sl['fallLine']}; "
        f"longest straight in the trees by pitch (median) {chk['straightness']['straightInTrees']}; S-turns {pl.s_turns}")
    return {"file": FILE, "lines": len(lines), "km": chk["km"], "checks": chk}


def main(argv):
    if not argv or argv[0].startswith("-"):
        sys.exit(__doc__)
    pack_dir = argv[0]
    only = argv[argv.index("--only") + 1] if "--only" in argv else None
    mp = os.path.join(pack_dir, "meta.json")
    meta = json.load(open(mp, encoding="utf-8"))
    if "--straightness" in argv:
        # the report on the pack's lines as they are, no rebuild: round one run (its name holds the text), or all of them
        name = argv[argv.index("--straightness") + 1] if len(argv) > argv.index("--straightness") + 1 else ""
        runs = json.load(open(os.path.join(pack_dir, "features.json"), encoding="utf-8")).get("runs", [])
        near = [r["points"] for r in runs if name and name.lower() in (r.get("name") or "").lower()]
        lines = json.load(open(os.path.join(pack_dir, FILE)))["lines"]
        import cover
        from scipy.spatial import cKDTree
        tr = [t[:, :2] for t in cover.tree_records(pack_dir, meta)]
        kd = cKDTree(np.concatenate(tr)) if tr else None
        print(json.dumps(straightness(lines, Heights(pack_dir, meta), near, kd), indent=1))
        return
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
