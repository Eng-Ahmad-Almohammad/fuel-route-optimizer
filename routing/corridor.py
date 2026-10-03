"""Place points (fuel stations) along a route: how far down the road they are and how far off it."""

import math
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass

from routing.geo import MILES_PER_DEGREE_LATITUDE, LonLat, approx_miles, haversine_miles

# Route points are thinned to roughly this spacing before matching; plenty for a corridor several miles wide.
SAMPLE_SPACING_MILES = 0.5
# Longitude degrees shrink towards the poles; size grid cells for the northernmost latitude the route reaches
# (capped well short of the pole) so a cell is never narrower than the corridor.
MAX_LATITUDE_FOR_CELL_SIZE = 80.0


@dataclass(frozen=True)
class RoutePosition:
    """Where a point sits relative to the route."""

    mile: float
    offset_miles: float


@dataclass(frozen=True)
class BoundingBox:
    """A latitude/longitude rectangle."""

    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float


class RouteCorridor:
    """A route plus a corridor of ``width_miles`` on each side, with fast "where is this point" lookups.

    Each route point gets a mile marker (distance along the road from the start). Points are bucketed into a
    grid whose cells are at least ``width_miles`` across, so a lookup only measures against the route points in
    the point's own cell and the eight around it.
    """

    def __init__(self, coordinates: list[LonLat], width_miles: float, distance_miles: float | None = None) -> None:
        """Index the route.

        ``distance_miles`` is the routing API's road distance; when given, mile markers are scaled to match it
        exactly so stop positions and the total distance agree.
        """
        if len(coordinates) < 2:
            raise ValueError("A route needs at least two points.")
        self.width_miles = width_miles
        miles = _cumulative_miles(coordinates)
        scale = distance_miles / miles[-1] if distance_miles and miles[-1] else 1.0
        self.points, self.miles = _sample(coordinates, [mile * scale for mile in miles])
        self.total_miles = self.miles[-1]
        max_latitude = min(max(abs(lat) for _, lat in self.points), MAX_LATITUDE_FOR_CELL_SIZE)
        self.cell_degrees = width_miles / (MILES_PER_DEGREE_LATITUDE * math.cos(math.radians(max_latitude)))
        self._grid: dict[tuple[int, int], list[int]] = defaultdict(list)
        for index, point in enumerate(self.points):
            self._grid[self._cell(point)].append(index)

    def bounding_box(self) -> BoundingBox:
        """Return the rectangle around the route, widened by the corridor width."""
        lons = [lon for lon, _ in self.points]
        lats = [lat for _, lat in self.points]
        return BoundingBox(
            min_lat=min(lats) - self.cell_degrees,
            min_lon=min(lons) - self.cell_degrees,
            max_lat=max(lats) + self.cell_degrees,
            max_lon=max(lons) + self.cell_degrees,
        )

    def locate(self, point: LonLat) -> RoutePosition | None:
        """Return the mile marker of the route point nearest to ``point``, or None if it is outside the corridor."""
        best_index, best_offset = -1, math.inf
        for index in self._nearby_indexes(point):
            offset = approx_miles(point, self.points[index])
            if offset < best_offset:
                best_index, best_offset = index, offset
        if best_offset > self.width_miles:
            return None
        return RoutePosition(mile=self.miles[best_index], offset_miles=best_offset)

    def _cell(self, point: LonLat) -> tuple[int, int]:
        return math.floor(point[0] / self.cell_degrees), math.floor(point[1] / self.cell_degrees)

    def _nearby_indexes(self, point: LonLat) -> Iterator[int]:
        column, row = self._cell(point)
        for d_column in (-1, 0, 1):
            for d_row in (-1, 0, 1):
                yield from self._grid.get((column + d_column, row + d_row), ())


def _cumulative_miles(coordinates: list[LonLat]) -> list[float]:
    miles = [0.0]
    for previous, current in zip(coordinates, coordinates[1:]):
        miles.append(miles[-1] + haversine_miles(previous, current))
    return miles


def _sample(coordinates: list[LonLat], miles: list[float]) -> tuple[list[LonLat], list[float]]:
    """Keep a point roughly every SAMPLE_SPACING_MILES, always keeping the first and last."""
    points, kept_miles = [coordinates[0]], [miles[0]]
    for point, mile in zip(coordinates[1:-1], miles[1:-1]):
        if mile - kept_miles[-1] >= SAMPLE_SPACING_MILES:
            points.append(point)
            kept_miles.append(mile)
    points.append(coordinates[-1])
    kept_miles.append(miles[-1])
    return points, kept_miles
