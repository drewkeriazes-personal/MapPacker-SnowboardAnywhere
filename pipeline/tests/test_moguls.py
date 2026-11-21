"""FEAT-059: mogul scoring and field painting."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from moguls import FIELD_FADE, GROOMED_CORE, corridor_extent, groomed_keep, paint_field, run_mogul_score, slope_window, soften_mask  # noqa: E402


def run(**kw):
    base = {"name": "Prima", "difficulty": "expert", "gladed": False, "area": False}
    base.update(kw)
    return base


def test_mogul_tag_wins():
    assert run_mogul_score(run(difficulty="easy", gladed=True), 5.0, None, 1.0, True, False) == 1.0


def test_groomed_blue_scores_zero():
    assert run_mogul_score(run(difficulty="intermediate"), 25.0, 10.0, 0.9, False, True) == 0.0


def test_never_groomed_expert_north_scores_high():
    assert run_mogul_score(run(), 28.0, 10.0, 0.0, False, True) == 1.0


def test_unknown_grooming_falls_back():
    s = run_mogul_score(run(difficulty="advanced"), 28.0, 180.0, None, False, False)
    assert abs(s - 0.7 * 0.9 * 1.0 * 0.7 * 0.8) < 1e-6


def test_occasionally_groomed_scores_lower_than_never():
    never = run_mogul_score(run(difficulty="advanced"), 28.0, 10.0, 0.0, False, True)
    few = run_mogul_score(run(difficulty="advanced"), 28.0, 10.0, 3 / 42, False, True)
    assert never > few > 0.3


def test_blue_left_ungroomed_scores_some():
    assert run_mogul_score(run(difficulty="intermediate"), 28.0, 10.0, 4 / 42, False, True) > 0.2


def test_steep_pitch_counts_not_the_runout():
    # Highline: 75th percentile 24 deg although the whole line averages 15
    assert run_mogul_score(run(), 24.0, 10.0, 0.0, False, False) > 0.7
    assert run_mogul_score(run(), 13.0, 10.0, 0.0, False, False) < 0.2


def test_cat_track_and_glades_zero():
    assert run_mogul_score(run(name="Minnie's Mile Road"), 28.0, 10.0, 0.0, False, True) == 0.0
    assert run_mogul_score(run(gladed=True), 28.0, 10.0, 0.0, False, True) == 0.0
    assert run_mogul_score(run(difficulty="easy"), 28.0, 10.0, 0.0, False, True) == 0.0
    assert run_mogul_score(run(), 8.0, 10.0, 0.0, False, True) == 0.0


def test_slope_window():
    v = slope_window(np.array([10.0, 17.5, 25.0, 37.5, 45.0]))
    assert np.allclose(v, [0.0, 0.5, 1.0, 0.5, 0.0])
    assert slope_window(25.0) == 1.0


def test_paint_field_edge_fade():
    t = np.zeros((100, 100), np.float32)
    # raster: x0 = 0, y1 = 200 (north edge), res 2: cell (r, c) covers x in [2c, 2c+2), y in (200-2r-2, 200-2r]
    paint_field(t, [(100.0, 180.0), (100.0, 20.0)], 10.0, 1.0, 2.0, 0.0, 200.0)
    mid = t[50, 50]
    assert mid > 0.99
    assert abs(t[50, 50 + 4] - 1 / 3) < 0.2       # 8 to 9 m out: inside the 3 m fade
    assert t[50, 50 + 6] == 0.0                   # 12 m out
    assert t[50, 50 - 6] == 0.0
    assert t[2, 50] == 0.0                        # 15 m past the north end


def test_corridor_extent_fades_gradually():
    # BUG-065: Milt's Face (advanced, 14 m half width) fades in over FIELD_FADE, painted past the run's edge
    half, edge = corridor_extent(14.0)
    assert half > 14.0 and edge == FIELD_FADE and half - edge >= 5.0
    # a narrow run still reaches full amplitude in its middle
    half, edge = corridor_extent(4.0)
    assert edge < half


def test_paint_field_smooth_fade():
    t = np.zeros((100, 100), np.float32)
    half, edge = corridor_extent(14.0)
    paint_field(t, [(100.0, 180.0), (100.0, 20.0)], half, 1.0, 2.0, 0.0, 200.0, edge=edge, smooth=True)
    row = t[50, 50:62]
    assert row[0] > 0.99 and row[3] > 0.99          # full out to 7 m
    assert np.all(np.diff(row) <= 1e-6)             # never rises going out
    assert np.max(np.abs(np.diff(row))) < 0.35      # at most 0.35 per 2 m cell (the old 3 m fade stepped 0.67)
    assert row[-1] == 0.0                            # gone past the painted half width (22 m out)


def test_soften_mask_ramps_from_the_edge():
    keep = np.ones((40, 40), bool)
    keep[:, :10] = False                             # trees west of x = 20 m (res 2)
    m = soften_mask(keep, 2.0)
    assert np.all(m[:, :10] == 0.0)
    r = m[20, 10:20]
    assert 0.0 <= r[0] < 0.2 and r[-1] == 1.0       # rises from the tree line to full over about 6 m
    assert np.all(np.diff(r) >= -1e-6)
    assert np.all(soften_mask(np.ones((8, 8), bool), 2.0) == 1.0)


def test_groomed_core_survives_a_bump_run_beside_it():
    """BUG-067: a groomer 9 m from a never-groomed run's line keeps its own core strip; past the midline the cells
    still go to the bump run (BUG-030)"""
    from scipy import ndimage
    res = 2.0
    groomed_line = np.zeros((40, 40), bool); groomed_line[:, 10] = True
    never_line = np.zeros((40, 40), bool); never_line[:, 14] = True      # 8 m away
    d_g = ndimage.distance_transform_edt(~groomed_line); d_u = ndimage.distance_transform_edt(~never_line)
    keep = groomed_keep(d_g, d_u, res)
    core = int(GROOMED_CORE // res)
    assert keep[:, 10 - core:10 + core + 1].all()          # the groomer's own strip, the side toward the bump run too
    assert not keep[:, 14].any()                            # the bump run's line stays ungroomed
    assert keep[:, 0].all()                                 # the far side still nearer the groomer
    # without a core the old rule handed the cells past the midline (12 and up) to the bump run
    assert not groomed_keep(d_g, d_u, res, core=0.0)[:, 13].any()
