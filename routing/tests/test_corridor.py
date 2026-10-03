"""Tests for placing points along a route."""

import pytest

from routing.corridor import RouteCorridor
from routing.geo import MILES_PER_DEGREE_LATITUDE

# A straight road heading north along longitude -95, one point every 0.1 degree of latitude (~6.9 miles).
NORTHBOUND = [(-95.0, 35.0 + step / 10) for step in range(31)]


def test_mile_markers_follow_the_road() -> None:
    corridor = RouteCorridor(NORTHBOUND, width_miles=10)

    position = corridor.locate((-95.0, 36.0))

    assert position is not None
    assert position.mile == pytest.approx(MILES_PER_DEGREE_LATITUDE, rel=0.01)
    assert position.offset_miles == pytest.approx(0, abs=0.01)
    assert corridor.total_miles == pytest.approx(3 * MILES_PER_DEGREE_LATITUDE, rel=0.01)


def test_points_outside_the_corridor_are_not_located() -> None:
    corridor = RouteCorridor(NORTHBOUND, width_miles=10)

    near = corridor.locate((-95.1, 36.5))  # ~5.6 miles west of the road
    far = corridor.locate((-95.3, 36.5))  # ~16.7 miles off

    assert near is not None
    assert near.offset_miles == pytest.approx(5.56, abs=0.1)
    assert far is None


def test_road_distance_rescales_mile_markers() -> None:
    corridor = RouteCorridor(NORTHBOUND, width_miles=10, distance_miles=250.0)

    assert corridor.total_miles == pytest.approx(250.0)
    assert corridor.miles[0] == 0


def test_bounding_box_covers_route_plus_corridor() -> None:
    corridor = RouteCorridor(NORTHBOUND, width_miles=10)

    box = corridor.bounding_box()

    assert box.min_lat < 35.0 < 38.0 < box.max_lat
    assert box.min_lon < -95.0 < box.max_lon


def test_route_needs_two_points() -> None:
    with pytest.raises(ValueError, match="at least two points"):
        RouteCorridor([(-95.0, 35.0)], width_miles=10)
