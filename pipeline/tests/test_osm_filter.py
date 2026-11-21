"""DATA-021: private runs and lifts (Big Sky's Yellowstone Club and Spanish Peaks neighbours) stay out of the pack."""
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import osm_filter as of

SQUARE = [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]]


def way(id_, tags, pts):
    return {"type": "way", "id": id_, "tags": tags, "geometry": [{"lon": x, "lat": y} for x, y in pts]}


def test_private_access_tags():
    assert of.is_private({"access": "private"})
    assert of.is_private({"access": "members"})
    assert of.is_private({"aerialway:access": "no"})
    assert of.is_private({"piste:access": "private"})
    assert not of.is_private({"access": "yes"})
    assert not of.is_private({})


def test_areas_from_osm_way_and_ring():
    club = way(7, {"landuse": "winter_sports", "name": "Club"}, SQUARE)
    areas = of.exclude_areas([{"name": "Club", "osm_way": 7}, {"name": "Band", "lonlat": [[20, 0], [30, 0], [30, 5], [20, 5]]}],
                             {"elements": [club]})
    assert [a["name"] for a in areas] == ["Club", "Band"]
    assert of.inside(5, 5, areas[0]["ring"]) and not of.inside(15, 5, areas[0]["ring"])
    assert of.inside(25, 2, areas[1]["ring"])          # an open ring closes itself


def test_missing_osm_way_is_reported_not_fatal():
    missing = []
    assert of.exclude_areas([{"name": "Gone", "osm_way": 99}], {"elements": []}, missing.append) == []
    assert missing and "99" in missing[0]


def test_excluded_needs_most_points_inside():
    areas = [{"name": "Club", "ring": SQUARE}]
    inside_run = way(1, {"piste:type": "downhill"}, [(1, 1), (5, 5), (9, 9)])
    edge_run = way(2, {"piste:type": "downhill"}, [(8, 5), (12, 5), (14, 5), (16, 5)])   # one point of four inside
    out_run = way(3, {"piste:type": "downhill"}, [(20, 20), (30, 30)])
    assert of.excluded(inside_run, areas) == "Club"
    assert of.excluded(edge_run, areas) is None        # a public run that only touches the boundary stays
    assert of.excluded(out_run, areas) is None
    assert of.excluded(way(4, {"access": "private"}, [(50, 50), (60, 60)]), areas) == "access"


def test_excluded_by_osm_id():
    # FEAT-223: resolve --alone lists the neighbour's own runs and lifts by OSM id, wherever their points lie
    areas = of.exclude_areas([{"name": "Club", "osm_ways": [11, "12"]}], {"elements": []})
    assert of.excluded(way(11, {"piste:type": "downhill"}, [(50, 50), (60, 60)]), areas) == "Club"
    assert of.excluded(way(12, {"aerialway": "chair_lift"}, [(1, 1), (2, 2)]), areas) == "Club"
    assert of.excluded(way(13, {"piste:type": "downhill"}, [(1, 1), (2, 2)]), areas) is None


def test_filter_elements_keeps_nodes_and_non_ski_ways():
    areas = [{"name": "Club", "ring": SQUARE}]
    els = [way(1, {"piste:type": "downhill"}, [(1, 1), (2, 2)]),
           way(2, {"aerialway": "chair_lift", "access": "private"}, [(40, 40), (50, 50)]),
           way(3, {"aerialway": "chair_lift"}, [(40, 40), (50, 50)]),
           way(4, {"landuse": "winter_sports"}, SQUARE),
           {"type": "node", "id": 5, "tags": {"aerialway": "pylon"}, "lat": 1, "lon": 1}]
    kept, dropped = of.filter_ski({"elements": els}, areas)
    assert [e["id"] for e in kept["elements"]] == [3, 4, 5]
    assert dropped == {"Club": 1, "access": 1}


def test_run_names_piste_name_first():
    """FEAT-296: Park City's way 987605843 is name=McConkeys (the lift), piste:name=Georgeanna (the run)"""
    assert of.run_names({"name": "McConkeys", "piste:name": "Georgeanna"}) == ("Georgeanna", "McConkeys")
    assert of.run_names({"piste:name": "Cinch"}) == ("Cinch", None)
    assert of.run_names({"name": "Born Free"}) == ("Born Free", None)
    assert of.run_names({"name": "Same", "piste:name": "Same"}) == ("Same", None)
    assert of.run_names({"name": " ", "piste:name": ""}) == (None, None)


def run(name, diff, length, x=0.0, groomed=True, **kw):
    return {"name": name, "difficulty": diff, "groomed": groomed, "area": False,
            "points": [[x, 0.0, 2500.0], [x, -length, 2500.0 - length / 4]], **kw}


def test_default_start_skips_nordic():
    """BUG-108 (Park City's 5K Nordic Loop): the longest intermediate is a Nordic trail; the start takes the downhill one"""
    nordic = run("5K Nordic Loop", "intermediate", 5000.0, pisteType="nordic")
    sled = run("Sled Hill", "intermediate", 3000.0, x=50.0, pisteType="sled")
    blue = run("Bonanza", "intermediate", 900.0, x=100.0)
    green = run("Home Run", "easy", 2000.0, x=150.0)
    assert of.is_downhill(blue) and not of.is_downhill(nordic)
    assert of.default_start_run([nordic, sled, blue, green]) is blue
    assert of.default_start_run([nordic, green]) is green          # no downhill intermediate: the longest downhill run
    assert of.default_start_run([nordic, sled]) is None
    assert of.default_start_run([nordic, blue], want="5K Nordic Loop") is nordic   # a named start_run stays as it is
