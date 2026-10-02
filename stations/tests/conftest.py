"""Fixtures with small stand-ins for the Census Gazetteer files and the fuel price list."""

import zipfile
from pathlib import Path

import pytest
from pytest_django.fixtures import Settings

GAZETTEER_HEADER = "USPS|GEOID|NAME|FUNCSTAT|INTPTLAT|INTPTLONG"

PLACES = [
    "OK|1|Big Cabin town|A|36.537602|-95.229368",
    "IN|2|Indianapolis city (balance)|F|39.776664|-86.145935",
    "TX|3|Town of Pecos city|A|31.406955|-103.493210",
    "NJ|4|Mahwah CDP|S|41.100000|-74.150000",
]
COUNTY_SUBDIVISIONS = [
    "NJ|5|Mahwah township|A|41.088000|-74.191000",
    "NJ|6|North Brunswick township|A|40.449000|-74.482000",
]
OVERRIDES = "name,state,latitude,longitude\nRuther Glen,VA,37.9408753,-77.4618647\n"
FUEL_PRICES = """OPIS Truckstop ID,Truckstop Name,Address,City,State,Rack ID,Retail Price
7,WOODSHED OF BIG CABIN,"I-44, EXIT 283 & US-69",Big Cabin,OK,307,3.00733333
20,PILOT TRAVEL CENTER #1243,I-70 EXIT 89,Indianapolis,IN,930,3.899
21,LOVES #1,I-20 EXIT 42,Pecos,TX,931,3.1
22,TA MAHWAH,I-287 EXIT 66,Mahwah,NJ,932,3.5
23,NOWHERE STOP,US-1,Atlantis,VA,933,2.9
"""


def write_gazetteer_zip(path: Path, rows: list[str]) -> Path:
    """Write rows as a Census-style pipe-delimited file inside a zip archive."""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(path.with_suffix(".txt").name, "\n".join([GAZETTEER_HEADER, *rows]) + "\n")
    return path


@pytest.fixture
def data_dir(tmp_path: Path, settings: Settings) -> Path:
    """Point settings.DATA_DIR at a temporary directory holding small versions of every data file."""
    census_dir = tmp_path / "census"
    census_dir.mkdir()
    write_gazetteer_zip(census_dir / "2025_Gaz_place_national.zip", PLACES)
    write_gazetteer_zip(census_dir / "2025_Gaz_cousubs_national.zip", COUNTY_SUBDIVISIONS)
    (tmp_path / "place_overrides.csv").write_text(OVERRIDES)
    (tmp_path / "fuel-prices-for-be-assessment.csv").write_text(FUEL_PRICES)
    settings.DATA_DIR = tmp_path
    return tmp_path
