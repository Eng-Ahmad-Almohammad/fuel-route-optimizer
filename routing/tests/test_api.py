"""Tests for the trip planning endpoint and map page."""

from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import pytest
from django.core.cache import cache
from django.test import Client

from routing.client import NoRouteError, RoutingServiceError
from stations.models import FuelStation, Place

TRIP = {"start": "Tulsa, OK", "finish": "Kansas City, MO"}


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    cache.clear()


@pytest.mark.usefixtures("places", "stations")
def test_post_plans_the_cheapest_stops(client: Client, fake_route: Callable[..., MagicMock]) -> None:
    fake_route()

    response = client.post("/api/route/", TRIP, content_type="application/json")

    body: dict[str, Any] = response.json()
    assert response.status_code == 200
    assert body["distance_miles"] == 215.0
    assert body["total_gallons"] == pytest.approx(21.5)
    # Buy at Tulsa only enough to reach the cheaper Midway stop, then the rest there; Far Away is off the road.
    assert [stop["name"] for stop in body["fuel_stops"]] == ["TULSA STOP", "MIDWAY STOP"]
    assert body["total_fuel_cost"] == pytest.approx(
        sum(stop["cost"] for stop in body["fuel_stops"]),
        abs=0.01,
    )
    assert body["stations_considered"] == 2
    assert body["cached"] is False
    assert body["map_url"].startswith("http://testserver/map/?start=Tulsa")
    kinds = [feature["properties"]["kind"] for feature in body["route"]["features"]]
    assert kinds == ["route", "start", "fuel_stop", "fuel_stop", "finish"]


@pytest.mark.usefixtures("places", "stations")
def test_repeat_requests_are_served_from_cache(client: Client, fake_route: Callable[..., MagicMock]) -> None:
    routing_api = fake_route()

    first = client.get("/api/route/", TRIP)
    second = client.get("/api/route/", {"start": "tulsa,ok", "finish": "Kansas City, mo"})

    assert first.json()["cached"] is False
    assert second.json()["cached"] is True
    assert second.json()["total_fuel_cost"] == first.json()["total_fuel_cost"]
    assert routing_api.call_count == 1


@pytest.mark.usefixtures("places")
@pytest.mark.parametrize(
    ("payload", "field", "message"),
    [
        ({"start": "Tulsa", "finish": "Kansas City, MO"}, "start", 'not in "City, ST" format'),
        ({"start": "Tulsa, OK", "finish": "Atlantis, VA"}, "finish", 'Unknown US place "Atlantis, VA"'),
        ({"start": "Tulsa, OK", "finish": "tulsa, ok"}, "non_field_errors", "must be different places"),
        ({"start": "Tulsa, OK"}, "finish", "required"),
    ],
)
def test_invalid_input(client: Client, payload: dict[str, str], field: str, message: str) -> None:
    response = client.post("/api/route/", payload, content_type="application/json")

    assert response.status_code == 400
    assert message in " ".join(response.json()[field])


@pytest.mark.usefixtures("places", "stations")
def test_no_route_is_reported(client: Client, fake_route: Callable[..., MagicMock]) -> None:
    fake_route(side_effect=NoRouteError("Could not find routable point"))

    response = client.get("/api/route/", TRIP)

    assert response.status_code == 422
    assert response.json() == {"detail": "Could not find routable point"}


@pytest.mark.usefixtures("places")
def test_trip_without_stations_is_infeasible(client: Client, fake_route: Callable[..., MagicMock]) -> None:
    fake_route()

    response = client.get("/api/route/", TRIP)

    assert response.status_code == 422
    assert "No fuel station within 500 miles" in response.json()["detail"]


@pytest.mark.usefixtures("places", "stations")
def test_routing_service_failure_is_a_bad_gateway(client: Client, fake_route: Callable[..., MagicMock]) -> None:
    fake_route(side_effect=RoutingServiceError("Routing service error 403: quota exceeded"))

    response = client.get("/api/route/", TRIP)

    assert response.status_code == 502
    assert "quota exceeded" in response.json()["detail"]


@pytest.mark.usefixtures("places", "stations")
def test_stations_in_the_same_town_keep_only_the_cheapest(
    client: Client,
    fake_route: Callable[..., MagicMock],
    stations: list[FuelStation],
) -> None:
    FuelStation.objects.create(
        opis_id=99,
        name="PRICIER MIDWAY STOP",
        address="I-44",
        city="Midway Stop",
        state="OK",
        rack_id=1,
        price="3.10",
        latitude=stations[1].latitude,
        longitude=stations[1].longitude,
    )
    fake_route()

    body = client.get("/api/route/", TRIP).json()

    assert body["stations_considered"] == 2
    assert "PRICIER MIDWAY STOP" not in [stop["name"] for stop in body["fuel_stops"]]


@pytest.mark.django_db
def test_map_page_renders(client: Client) -> None:
    response = client.get("/map/", {"start": "Tulsa, OK", "finish": "Kansas City, MO"})

    assert response.status_code == 200
    assert b"leaflet" in response.content
    assert b"/api/route/" in response.content


def test_place_str(places: dict[str, Place]) -> None:
    assert str(places["kansas_city"]) == "Kansas City, MO"
