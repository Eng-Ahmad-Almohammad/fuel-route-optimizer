"""Geocode the truck stop cities that are missing from the Census Gazetteer.

This is a one-off data preparation step, not part of serving requests: it is only needed again when the fuel
price list changes. Results are appended to ``data/place_overrides.csv``, which is committed to the repo.
"""

import csv
import time
from typing import Any

import requests
from django.core.management.base import BaseCommand

from stations.datafiles import fuel_prices_path, load_gazetteer, place_overrides_path, read_station_rows
from stations.gazetteer import normalize_place_name

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
# Nominatim's usage policy: identify the application and send at most one request per second.
USER_AGENT = "fuel-route-optimizer/1.0 (one-off data preparation)"
SECONDS_BETWEEN_REQUESTS = 1.1
OVERRIDE_FIELDS = ["name", "state", "latitude", "longitude"]


def _nominatim_search(params: dict[str, str | int]) -> tuple[float, float] | None:
    response = requests.get(
        NOMINATIM_URL,
        params={**params, "countrycodes": "us", "format": "jsonv2", "limit": 1},
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    response.raise_for_status()
    results: list[dict[str, Any]] = response.json()
    if not results:
        return None
    return float(results[0]["lat"]), float(results[0]["lon"])


def nominatim_lookup(city: str, state: str) -> tuple[float, float] | None:
    """Return the (latitude, longitude) of a US city, or None when OpenStreetMap does not know it.

    Tries a structured city/state search first, then a free-text one, which also matches places that
    OpenStreetMap does not tag as a city (e.g. "Pueblo of Acoma").
    """
    coordinates = _nominatim_search({"city": city, "state": state})
    if coordinates is None:
        time.sleep(SECONDS_BETWEEN_REQUESTS)
        coordinates = _nominatim_search({"q": f"{city}, {state}"})
    return coordinates


class Command(BaseCommand):
    """Look up cities from the fuel price list that the Census Gazetteer cannot resolve."""

    help = "Geocode fuel price list cities missing from the Census Gazetteer into data/place_overrides.csv."

    def handle(self, *args: Any, **options: Any) -> None:
        """Find the unresolved (city, state) pairs and geocode each one with Nominatim."""
        gazetteer = load_gazetteer()
        missing = sorted(
            {
                (row.city, row.state)
                for row in read_station_rows(fuel_prices_path())
                if (normalize_place_name(row.city), row.state) not in gazetteer
            },
        )
        self.stdout.write(f"{len(missing)} cities are missing from the gazetteer.")
        found, not_found = self._geocode(missing)
        self._append_overrides(found)
        self.stdout.write(self.style.SUCCESS(f"Added {len(found)} places to {place_overrides_path()}."))
        if not_found:
            self.stdout.write(self.style.WARNING(f"Not found: {', '.join(f'{c}, {s}' for c, s in not_found)}"))

    def _geocode(self, cities: list[tuple[str, str]]) -> tuple[list[dict[str, Any]], list[tuple[str, str]]]:
        found: list[dict[str, Any]] = []
        not_found: list[tuple[str, str]] = []
        for index, (city, state) in enumerate(cities):
            if index:
                time.sleep(SECONDS_BETWEEN_REQUESTS)
            coordinates = nominatim_lookup(city, state)
            if coordinates is None:
                not_found.append((city, state))
                continue
            latitude, longitude = coordinates
            found.append({"name": city, "state": state, "latitude": latitude, "longitude": longitude})
        return found, not_found

    def _append_overrides(self, rows: list[dict[str, Any]]) -> None:
        path = place_overrides_path()
        is_new = not path.exists()
        with path.open("a", encoding="utf-8", newline="") as overrides:
            writer = csv.DictWriter(overrides, fieldnames=OVERRIDE_FIELDS)
            if is_new:
                writer.writeheader()
            writer.writerows(rows)
