import json, sys, math, numpy as np
sys.path.insert(0, "pipeline")
import traffic as T
pk = sys.argv[1]
meta = json.load(open(pk + "/meta.json", encoding="utf-8")); feats = json.load(open(pk + "/features.json", encoding="utf-8"))
D, g = T.density(pk, meta, feats, tree_lines=False)
np.save(sys.argv[2], D)
rgb, _ = T.read_traffic(pk, meta); F = rgb[..., 2][:g.H, :g.W].astype(np.float32) / 255
np.save(sys.argv[2].replace(".npy", "_final.npy"), F)
# mask canopy on the traffic grid
_, can = T.read_mask(pk, meta, g)
print("cells ridden rough %.3f final %.3f" % ((D > 0).mean(), (F > 0).mean()))
print("in canopy (A>0.35): rough share of density %.3f, final %.3f" % (D[can > .35].sum() / D.sum(), F[can > .35].sum() / F.sum()))
lift_tops = [(s[0], s[1]) for l in feats["lifts"] for s in l["stations"]]
rows = []
for r in feats["runs"]:
    p = np.asarray([q[:2] for q in r["points"]]); 
    if len(p) < 2: continue
    rr, cc = g.cell(p[:, 0], p[:, 1]); ok = g.inside(rr, cc)
    if not ok.any(): continue
    d = float(np.percentile(D[rr[ok], cc[ok]], 75))
    top = max(r["points"], key=lambda q: q[2])
    nt = any(math.hypot(top[0] - x, top[1] - y) < 150 for x, y in lift_tops)
    rows.append((r.get("name"), r.get("difficulty"), r.get("mogulScore", 0), nt, d))
json.dump(rows, open(sys.argv[2].replace(".npy", "_runs.json"), "w"))
a = np.array([x[4] for x in rows]); nt = np.array([x[3] for x in rows]); ms = np.array([x[2] for x in rows])
print("runs %d; near top %d; density p75 along line: near-top median %.2f, others %.2f" % (len(rows), nt.sum(), np.median(a[nt]), np.median(a[~nt])))
m = ms > 0
print("mogul-scoring runs %d: density quartiles %s; near top %d" % (m.sum(), np.percentile(a[m], [10, 25, 50, 75, 90]).round(2), nt[m].sum()))
from scipy.stats import spearmanr
print("spearman(density, near_top) over scoring runs: %.2f" % spearmanr(a[m], nt[m]).correlation)
