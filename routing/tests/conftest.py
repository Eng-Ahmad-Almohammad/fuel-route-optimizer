"""Shared fixtures: a few places and stations, and a fake routing API."""

from collections.abc import Callable
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from routing.client import Route
from stations.models import FuelStation, Place

# A straight road north from Tulsa, OK (36.15, -95.99) to Kansas City, MO (39.10, -94.58), ~215 miles.
TULSA = (-95.99, 36.15)
KANSAS_CITY = (-94.58, 39.10)


def straight_line(
    start: tuple[float, float],
    finish: tuple[float, float],
    steps: int = 200,
) -> list[tuple[float, float]]:
    """Return evenly spaced points between two (longitude, latitude) points."""
    return [
        (start[0] + (finish[0] - start[0]) * step / steps, start[1] + (finish[1] - start[1]) * step / steps)
        for step in range(steps + 1)
    ]


@pytest.fixture
def places(db: None) -> dict[str, Place]:
    """Tulsa and Kansas City."""
    return {
        "tulsa": Place.objects.create(key="tulsa", state="OK", name="Tulsa", latitude=TULSA[1], longitude=TULSA[0]),
        "kansas_city": Place.objects.create(
            key="kansascity",
            state="MO",
            name="Kansas City",
            latitude=KANSAS_CITY[1],
            longitude=KANSAS_CITY[0],
        ),
    }


@pytest.fixture
def stations(db: None) -> list[FuelStation]:
    """Two stations on the road (the cheaper one 40% of the way) and a cheap one far off it."""
    rows = [
        (1, "TULSA STOP", 36.15, -95.99, "3.40"),
        (2, "MIDWAY STOP", 37.33, -95.43, "2.90"),
        (3, "FAR AWAY STOP", 37.33, -98.00, "2.10"),
    ]
    return [
        FuelStation.objects.create(
            opis_id=opis_id,
            name=name,
            address="I-44",
            city=name.title(),
            state="OK",
            rack_id=1,
            price=Decimal(price),
            latitude=latitude,
            longitude=longitude,
        )
        for opis_id, name, latitude, longitude, price in rows
    ]


@pytest.fixture
def fake_route(mocker: MockerFixture) -> Callable[..., MagicMock]:
    """Patch the routing API call to return a straight road between the requested points."""

    def install(distance_miles: float = 215.0, side_effect: Exception | None = None) -> MagicMock:
        def route(start: tuple[float, float], finish: tuple[float, float]) -> Route:
            if side_effect is not None:
                raise side_effect
            return Route(straight_line(start, finish), distance_miles=distance_miles, duration_seconds=3 * 3600)

        return mocker.patch("routing.planner.fetch_route", side_effect=route)

    return install
