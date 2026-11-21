"""Towers for a chair or gondola whose OSM way has no aerialway=pylon nodes (BUG-102).

Some OSM lifts are drawn station to station with no pylons (Big Sky's Explorer Gondola Lower and Upper and One and
Only, Breckenridge's FIVE SuperChair). The pack then carried `towers: []` and only the game's fallback stood towers
on them. The pipeline now spaces them itself, on the DEM, with the same rule as that fallback (game
`src/world/Lifts.ts`: one every 140 m on the straight line between the end stations, 14 m on a gondola, 11 m on a
chair), so the pack says where they stand and the look does not change. The lift gets `towersSpaced: true`.
"""
import math

AERIAL = ("chair_lift", "gondola", "mixed_lift", "cable_car")   # lifts that hang on towers; surface lifts are the game's
GONDOLA = ("gondola", "mixed_lift", "cable_car")                # the game's 'gondola' kind
SPACING = 140.0                                                 # m between spaced towers, as the game's fallback


def spaced_towers(a, b, aw, ground):
    """Towers [x, y, zGround, height] evenly along a..b (the end stations, x y in pack metres) for lift type aw.
    ground(x, y) is the DEM height. Empty for a surface lift or a line shorter than two spacings."""
    if aw not in AERIAL:
        return []
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = max(1, math.floor(math.hypot(dx, dy) / SPACING))
    h = 14.0 if aw in GONDOLA else 11.0
    out = []
    for i in range(1, n):
        x, y = a[0] + dx * i / n, a[1] + dy * i / n
        out.append([x, y, float(ground(x, y)), h])
    return out
