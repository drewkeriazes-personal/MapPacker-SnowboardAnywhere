"""BUG-102: towers spaced along a chair or gondola whose OSM way has no pylons, as the game's fallback would."""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import lift_towers as lt  # noqa: E402


def ground(x, y):
    return 2000.0 + 0.1 * y


def test_gondola_every_140_m():
    t = lt.spaced_towers([0.0, 0.0], [0.0, 1351.0], "gondola", ground)   # Explorer Gondola Lower, 1351 m
    assert len(t) == 8                                                    # floor(1351 / 140) = 9 spans
    assert all(h == 14.0 for *_, h in t)
    ys = [y for _, y, _, _ in t]
    assert ys == sorted(ys) and abs(ys[0] - 1351.0 / 9) < 1e-9
    assert all(z == ground(x, y) for x, y, z, _ in t)


def test_chair_height_and_short_and_surface_lifts():
    t = lt.spaced_towers([0.0, 0.0], [1012.0, 0.0], "chair_lift", ground)   # FIVE SuperChair, 1012 m
    assert len(t) == 6 and all(h == 11.0 for *_, h in t)
    assert lt.spaced_towers([0.0, 0.0], [250.0, 0.0], "chair_lift", ground) == []   # one span: the game adds none either
    assert lt.spaced_towers([0.0, 0.0], [900.0, 0.0], "t-bar", ground) == []        # surface lifts stay the game's


def test_rule_matches_the_game(game_file):
    ts = open(game_file("game", "src", "world", "Lifts.ts"), encoding="utf-8").read()
    assert "kind === 'gondola' ? 14 : 11" in ts
    assert re.search(r"kind === 'surface' \? 60 : 140\)", ts)
    assert "type === 'gondola' || type === 'cable_car' || type === 'mixed_lift'" in ts
