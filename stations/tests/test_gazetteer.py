"""Tests for building the place gazetteer."""

from pathlib import Path

from stations.datafiles import load_gazetteer
from stations.gazetteer import PRIORITY_COUNTY_SUBDIVISION, PRIORITY_OVERRIDE, PRIORITY_PLACE


def test_census_suffixes_are_stripped(data_dir: Path) -> None:
    gazetteer = load_gazetteer()

    assert gazetteer[("indianapolis", "IN")].name == "Indianapolis"
    assert gazetteer[("pecos", "TX")].name == "Pecos"
    assert gazetteer[("bigcabin", "OK")].latitude == 36.537602


def test_places_take_precedence_over_county_subdivisions(data_dir: Path) -> None:
    gazetteer = load_gazetteer()

    mahwah = gazetteer[("mahwah", "NJ")]
    assert mahwah.priority == PRIORITY_PLACE
    assert mahwah.latitude == 41.1


def test_county_subdivisions_and_overrides_fill_gaps(data_dir: Path) -> None:
    gazetteer = load_gazetteer()

    assert gazetteer[("northbrunswick", "NJ")].priority == PRIORITY_COUNTY_SUBDIVISION
    assert gazetteer[("rutherglen", "VA")].priority == PRIORITY_OVERRIDE


def test_missing_overrides_file_is_ignored(data_dir: Path) -> None:
    (data_dir / "place_overrides.csv").unlink()

    gazetteer = load_gazetteer()

    assert ("rutherglen", "VA") not in gazetteer
    assert ("bigcabin", "OK") in gazetteer
