"""Plan a trip: route between two places, stations along it, and the cheapest fuel stops."""

from dataclasses import dataclass
from typing import Any

from routing.client import Route, fetch_route
from routing.corridor import RouteCorridor
from routing.optimizer import Purchase, StationStop, plan_purchases
from stations.models import FuelStation, Place

VEHICLE_RANGE_MILES = 500.0
VEHICLE_MILES_PER_GALLON = 10.0
# Stations are placed at their town's center, so allow for towns that sit a few miles off the highway.
CORRIDOR_WIDTH_MILES = 10.0
# Each stop is counted as costing this much of the driver's time, so the plan doesn't stop for a gallon to save
# a few cents. On cross-country trips this cuts stops by more than half for under 1% more fuel.
STOP_COST_DOLLARS = 5.0
# The tank starts empty; the first fill-up can be at any station this close to the start.
START_RADIUS_MILES = 25.0

STATION_FIELDS = ("opis_id", "name", "address", "city", "state", "price", "latitude", "longitude")


@dataclass(frozen=True)
class StationOnRoute:
    """A fuel station inside the route corridor."""

    station: dict[str, Any]
    mile: float
    offset_miles: float


def plan_trip(start: Place, finish: Place) -> dict[str, Any]:
    """Return the route, fuel stops and total fuel cost between two places as a JSON-ready dict."""
    route = fetch_route((start.longitude, start.latitude), (finish.longitude, finish.latitude))
    corridor = RouteCorridor(route.coordinates, CORRIDOR_WIDTH_MILES, route.distance_miles)
    candidates = stations_along(corridor)
    purchases = plan_purchases(
        [StationStop(mile=candidate.mile, price=float(candidate.station["price"])) for candidate in candidates],
        total_miles=corridor.total_miles,
        range_miles=VEHICLE_RANGE_MILES,
        miles_per_gallon=VEHICLE_MILES_PER_GALLON,
        stop_cost=STOP_COST_DOLLARS,
        start_radius_miles=START_RADIUS_MILES,
    )
    stops = [_stop_json(candidates[purchase.station_index], purchase) for purchase in purchases]
    return {
        "start": _place_json(start),
        "finish": _place_json(finish),
        "distance_miles": round(corridor.total_miles, 1),
        "duration_hours": round(route.duration_seconds / 3600, 1),
        "total_gallons": round(sum(purchase.gallons for purchase in purchases), 2),
        "total_fuel_cost": round(sum(purchase.cost for purchase in purchases), 2),
        "fuel_stops": stops,
        "stations_considered": len(candidates),
        "assumptions": {
            "range_miles": VEHICLE_RANGE_MILES,
            "miles_per_gallon": VEHICLE_MILES_PER_GALLON,
            "tank_at_start": "empty; the first stop is within "
            f"{START_RADIUS_MILES:g} miles of the start and pays for the miles driven to reach it",
            "corridor_width_miles": CORRIDOR_WIDTH_MILES,
            "stop_cost_dollars": STOP_COST_DOLLARS,
        },
        "route": _route_geojson(route, corridor, start, finish, stops),
    }


def stations_along(corridor: RouteCorridor) -> list[StationOnRoute]:
    """Return the stations inside the corridor, sorted by mile; at each spot only the cheapest is kept."""
    box = corridor.bounding_box()
    rows = FuelStation.objects.filter(
        latitude__range=(box.min_lat, box.max_lat),
        longitude__range=(box.min_lon, box.max_lon),
    ).values(*STATION_FIELDS)
    cheapest_at_mile: dict[float, StationOnRoute] = {}
    for row in rows:
        position = corridor.locate((row["longitude"], row["latitude"]))
        if position is None:
            continue
        # Stations in the same town share coordinates and therefore a mile marker; only the cheapest matters.
        current = cheapest_at_mile.get(position.mile)
        if current is None or row["price"] < current.station["price"]:
            cheapest_at_mile[position.mile] = StationOnRoute(row, position.mile, position.offset_miles)
    return sorted(cheapest_at_mile.values(), key=lambda candidate: candidate.mile)


def _stop_json(candidate: StationOnRoute, purchase: Purchase) -> dict[str, Any]:
    station = candidate.station
    return {
        "opis_id": station["opis_id"],
        "name": station["name"],
        "address": station["address"],
        "city": station["city"],
        "state": station["state"],
        "latitude": station["latitude"],
        "longitude": station["longitude"],
        "mile_marker": round(candidate.mile, 1),
        "price_per_gallon": float(station["price"]),
        "gallons": round(purchase.gallons, 2),
        "cost": round(purchase.cost, 2),
    }


def _place_json(place: Place) -> dict[str, Any]:
    return {"name": place.name, "state": place.state, "latitude": place.latitude, "longitude": place.longitude}


def _point_feature(longitude: float, latitude: float, properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [longitude, latitude]},
        "properties": properties,
    }


def _route_geojson(
    route: Route,
    corridor: RouteCorridor,
    start: Place,
    finish: Place,
    stops: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return the route line (thinned to the corridor's sample points) with pins for start, finish and stops."""
    line = {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": [list(point) for point in corridor.points]},
        "properties": {"kind": "route", "distance_miles": round(route.distance_miles, 1)},
    }
    pins = [
        _point_feature(start.longitude, start.latitude, {"kind": "start", "name": str(start)}),
        *(
            _point_feature(
                stop["longitude"],
                stop["latitude"],
                {"kind": "fuel_stop", "name": stop["name"], "price_per_gallon": stop["price_per_gallon"]},
            )
            for stop in stops
        ),
        _point_feature(finish.longitude, finish.latitude, {"kind": "finish", "name": str(finish)}),
    ]
    return {"type": "FeatureCollection", "features": [line, *pins]}
