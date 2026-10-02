"""Load the place gazetteer and the truck stop fuel prices into the database."""

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from stations.datafiles import fuel_prices_path, load_gazetteer, read_station_rows
from stations.gazetteer import GazetteerEntry, normalize_place_name
from stations.models import FuelStation, Place

BATCH_SIZE = 5000


def load_places(gazetteer: dict[tuple[str, str], GazetteerEntry]) -> int:
    """Replace all places with the gazetteer entries and return how many were stored."""
    Place.objects.all().delete()
    places = Place.objects.bulk_create(
        (
            Place(key=entry.key, state=entry.state, name=entry.name, latitude=entry.latitude, longitude=entry.longitude)
            for entry in gazetteer.values()
        ),
        batch_size=BATCH_SIZE,
    )
    return len(places)


def load_stations(path: Path, gazetteer: dict[tuple[str, str], GazetteerEntry]) -> tuple[int, list[str]]:
    """Replace all fuel stations with the rows of the price list.

    Each station is placed at the coordinates of its city. Returns the number of stations stored and the
    "City, ST" names that could not be located (those stations are skipped).
    """
    stations: list[FuelStation] = []
    unresolved: set[str] = set()
    for row in read_station_rows(path):
        entry = gazetteer.get((normalize_place_name(row.city), row.state))
        if entry is None:
            unresolved.add(f"{row.city}, {row.state}")
            continue
        stations.append(
            FuelStation(
                opis_id=row.opis_id,
                name=row.name,
                address=row.address,
                city=row.city,
                state=row.state,
                rack_id=row.rack_id,
                price=row.price,
                latitude=entry.latitude,
                longitude=entry.longitude,
            ),
        )
    FuelStation.objects.all().delete()
    FuelStation.objects.bulk_create(stations, batch_size=BATCH_SIZE)
    return len(stations), sorted(unresolved)


class Command(BaseCommand):
    """Build the Place and FuelStation tables from the files in ``data/``."""

    help = "Load US places (Census Gazetteer) and truck stop fuel prices into the database."

    def add_arguments(self, parser: CommandParser) -> None:
        """Allow loading a different fuel price list."""
        parser.add_argument("--prices", type=Path, default=fuel_prices_path(), help="Fuel price list CSV.")

    def handle(self, *args: Any, **options: Any) -> None:
        """Rebuild both tables in a single transaction."""
        gazetteer = load_gazetteer()
        with transaction.atomic():
            place_count = load_places(gazetteer)
            station_count, unresolved = load_stations(options["prices"], gazetteer)
        self.stdout.write(self.style.SUCCESS(f"Loaded {place_count} places and {station_count} fuel stations."))
        if unresolved:
            self.stdout.write(
                self.style.WARNING(
                    f"Skipped stations in {len(unresolved)} unknown cities: {', '.join(unresolved)}. "
                    "Run `geocode_missing_places` to add them.",
                ),
            )
