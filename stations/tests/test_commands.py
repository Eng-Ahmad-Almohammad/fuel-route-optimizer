"""Tests for the data loading and geocoding management commands."""

import csv
from decimal import Decimal
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from django.core.management import call_command
from pytest_mock import MockerFixture

from stations.models import FuelStation, Place


@pytest.mark.django_db
def test_load_fuel_data_places_stations_at_their_city(data_dir: Path) -> None:
    out = StringIO()

    call_command("load_fuel_data", stdout=out)

    big_cabin = FuelStation.objects.get(opis_id=7)
    assert (big_cabin.latitude, big_cabin.longitude) == (36.537602, -95.229368)
    assert big_cabin.price == Decimal("3.00733333")
    assert FuelStation.objects.count() == 4
    assert Place.objects.filter(key="indianapolis", state="IN").exists()
    assert "Atlantis, VA" in out.getvalue()


@pytest.mark.django_db
def test_load_fuel_data_replaces_previous_rows(data_dir: Path) -> None:
    call_command("load_fuel_data", stdout=StringIO())
    call_command("load_fuel_data", stdout=StringIO())

    assert FuelStation.objects.count() == 4
    assert Place.objects.filter(key="bigcabin").count() == 1


def _nominatim_response(results: list[dict[str, str]]) -> MagicMock:
    response = MagicMock()
    response.json.return_value = results
    return response


def test_geocode_missing_places_appends_found_cities(data_dir: Path, mocker: MockerFixture) -> None:
    mocker.patch("stations.management.commands.geocode_missing_places.time.sleep")
    get = mocker.patch(
        "stations.management.commands.geocode_missing_places.requests.get",
        side_effect=[_nominatim_response([]), _nominatim_response([{"lat": "37.1", "lon": "-77.2"}])],
    )
    out = StringIO()

    call_command("geocode_missing_places", stdout=out)

    # Structured search found nothing, so the free-text fallback was used.
    assert [call.kwargs["params"].get("q") for call in get.call_args_list] == [None, "Atlantis, VA"]
    with (data_dir / "place_overrides.csv").open() as overrides:
        rows = list(csv.DictReader(overrides))
    assert rows[-1] == {"name": "Atlantis", "state": "VA", "latitude": "37.1", "longitude": "-77.2"}
    assert "Added 1 places" in out.getvalue()


def test_geocode_missing_places_reports_unknown_cities(data_dir: Path, mocker: MockerFixture) -> None:
    (data_dir / "place_overrides.csv").unlink()
    mocker.patch("stations.management.commands.geocode_missing_places.time.sleep")
    mocker.patch(
        "stations.management.commands.geocode_missing_places.requests.get",
        return_value=_nominatim_response([]),
    )
    out = StringIO()

    call_command("geocode_missing_places", stdout=out)

    assert "Not found: Atlantis, VA" in out.getvalue()
    assert (data_dir / "place_overrides.csv").read_text() == "name,state,latitude,longitude\n"
