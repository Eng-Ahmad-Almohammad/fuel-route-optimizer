"""Client for the OpenRouteService directions API, the only external service called while serving requests."""

from dataclasses import dataclass
from typing import Any

import requests
from django.conf import settings

from routing.geo import LonLat

DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/{profile}/geojson"


class RoutingError(Exception):
    """The routing API could not produce a route."""


class NoRouteError(RoutingError):
    """There is no drivable route between the two places."""


class RoutingServiceError(RoutingError):
    """The routing API is unreachable, rejected our key, or rate limited us."""


@dataclass(frozen=True)
class Route:
    """A driving route: the road as a line of points plus its length."""

    coordinates: list[LonLat]
    distance_miles: float
    duration_seconds: float


def fetch_route(start: LonLat, finish: LonLat) -> Route:
    """Ask OpenRouteService for the driving route between two points (one HTTP request)."""
    body = {
        "coordinates": [list(start), list(finish)],
        "units": "mi",
        "instructions": False,
        "geometry_simplify": True,
        # Snap each point to the nearest road. -1 asks for no limit, but the public API caps snapping at 350 m,
        # so a town center farther than that from any road fails with NoRouteError (see README, Known limitations).
        "radiuses": [-1, -1],
    }
    try:
        response = requests.post(
            DIRECTIONS_URL.format(profile=settings.OPENROUTESERVICE_PROFILE),
            json=body,
            headers={"Authorization": settings.OPENROUTESERVICE_API_KEY},
            timeout=settings.OPENROUTESERVICE_TIMEOUT_SECONDS,
        )
    except requests.RequestException as error:
        raise RoutingServiceError(f"Could not reach the routing service: {error}") from error
    return _parse_response(response)


def _parse_response(response: requests.Response) -> Route:
    if response.status_code == 404:
        raise NoRouteError(_error_message(response))
    if not response.ok:
        raise RoutingServiceError(f"Routing service error {response.status_code}: {_error_message(response)}")
    feature = response.json()["features"][0]
    summary = feature["properties"]["summary"]
    return Route(
        coordinates=[(lon, lat) for lon, lat in feature["geometry"]["coordinates"]],
        distance_miles=float(summary["distance"]),
        duration_seconds=float(summary.get("duration", 0.0)),
    )


def _error_message(response: requests.Response) -> str:
    try:
        payload: Any = response.json()
    except ValueError:
        return response.text[:200]
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        return str(error.get("message", error))
    return str(error or payload)
