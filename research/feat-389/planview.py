"""Plan views of tree line variants over the hillshade and the rough traffic (red), runs in blue."""
import json, sys, numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, "pipeline")
import traffic as T
pk = "packs/vail-main"; meta = json.load(open(pk + "/meta.json", encoding="utf-8")); feats = json.load(open(pk + "/features.json", encoding="utf-8"))
g = T.Grid(meta); D = np.load("packs/rough_main.npy")
z = T.read_heights(pk, meta, g)
boxes = {"steep-and-deep": (1450, -4120, 2050, -3050), "champagne-cjs": (1000, -4400, 1750, -3000), "shangri-la": (1500, -900, 2300, 200)}
variants = sys.argv[1:]
S = 2  # px per 4 m cell
for name, (x0, y0, x1, y1) in boxes.items():
    r0, r1 = int((g.yT - y1) / 4), int((g.yT - y0) / 4); c0, c1 = int((x0 - g.x0) / 4), int((x1 - g.x0) / 4)
    zz = z[r0:r1, c0:c1].astype(np.float64); gy, gx = np.gradient(zz, 4.0)
    hs = np.clip(0.6 + 0.6 * (-gx * 0.7 + gy * 0.7) / np.hypot(1, np.hypot(gx, gy)), 0, 1)
    d = D[r0:r1, c0:c1]
    base = np.stack([hs * 235 * (1 - 0.6 * d) + 255 * 0.6 * d, hs * 235 * (1 - 0.6 * d), hs * 235 * (1 - 0.6 * d)], -1).astype(np.uint8)
    tiles = []
    for v in variants:
        im = Image.fromarray(base).resize(((c1 - c0) * S, (r1 - r0) * S)); dr = ImageDraw.Draw(im)
        px = lambda x, y: ((x - x0) / 4 * S, (y1 - y) / 4 * S)
        for r in feats["runs"]:
            p = [px(q[0], q[1]) for q in r["points"]]
            if len(p) > 1: dr.line(p, fill=(40, 90, 230), width=3)
        for ln in json.load(open(f"packs/treeLines-{v}.json"))["lines"]:
            a = np.asarray(ln["p"]).reshape(-1, 4)
            if a[:, 0].max() < x0 or a[:, 0].min() > x1 or a[:, 1].max() < y0 or a[:, 1].min() > y1: continue
            st = a[:, 3].mean()
            dr.line([px(x, y) for x, y in a[:, :2]], fill=(int(20 + 60 * (1 - st)), int(120 + 60 * (1 - st)), 20), width=max(1, int(1 + 2 * st)))
        dr.rectangle([0, 0, 120, 22], fill=(255, 255, 255)); dr.text((6, 5), v, fill=(0, 0, 0))
        tiles.append(im)
    W = sum(t.width for t in tiles) + 6 * (len(tiles) - 1)
    out = Image.new("RGB", (W, tiles[0].height), (255, 255, 255)); x = 0
    for t in tiles: out.paste(t, (x, 0)); x += t.width + 6
    out.save(f"packs/plan-{name}.png"); print(name, out.size)
