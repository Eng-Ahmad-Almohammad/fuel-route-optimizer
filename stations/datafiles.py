"""Locations and readers for the data files in ``data/``."""

import csv
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from django.conf import settings

from stations.gazetteer import GazetteerEntry, build_gazetteer


def fuel_prices_path() -> Path:
    """Return the path of the cleaned OPIS fuel price list."""
    return Path(settings.DATA_DIR) / "fuel-prices-for-be-assessment.csv"


def place_overrides_path() -> Path:
    """Return the path of the coordinates for places missing from the Census Gazetteer."""
    return Path(settings.DATA_DIR) / "place_overrides.csv"


def load_gazetteer() -> dict[tuple[str, str], GazetteerEntry]:
    """Build the place index from the Census Gazetteer files plus the committed overrides."""
    census_dir = Path(settings.DATA_DIR) / "census"
    return build_gazetteer(
        census_dir / "2025_Gaz_place_national.zip",
        census_dir / "2025_Gaz_cousubs_national.zip",
        place_overrides_path(),
    )


@dataclass(frozen=True)
class StationRow:
    """One row of the fuel price list."""

    opis_id: int
    name: str
    address: str
    city: str
    state: str
    rack_id: int
    price: Decimal


def read_station_rows(path: Path) -> list[StationRow]:
    """Read the fuel price list CSV."""
    with path.open(encoding="utf-8-sig", newline="") as prices:
        return [
            StationRow(
                opis_id=int(row["OPIS Truckstop ID"]),
                name=row["Truckstop Name"].strip(),
                address=row["Address"].strip(),
                city=row["City"].strip(),
                state=row["State"].strip(),
                rack_id=int(row["Rack ID"]),
                price=Decimal(row["Retail Price"]),
            )
            for row in csv.DictReader(prices)
        ]
