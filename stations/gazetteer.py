"""US place-name gazetteer built from the Census Bureau Gazetteer files.

The fuel price list only gives each truck stop a city and state, and the API accepts locations as
"City, ST". Both are resolved to coordinates offline with the Census Gazetteer files in ``data/census``
so that no geocoding API is called at request time.
"""

import csv
import io
import itertools
import re
import unicodedata
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

# Lower number wins when two gazetteer entries normalize to the same (name, state) key.
PRIORITY_PLACE = 0
PRIORITY_PLACE_ALIAS = 1
PRIORITY_COUNTY_SUBDIVISION = 2
PRIORITY_COUNTY_SUBDIVISION_ALIAS = 3
PRIORITY_OVERRIDE = 4

_ABBREVIATIONS = {
    "st": "saint",
    "ste": "sainte",
    "ft": "fort",
    "mt": "mount",
    "n": "north",
    "s": "south",
    "e": "east",
    "w": "west",
}

# Legal/statistical area descriptions the Census appends to names, e.g. "Abbeville city", "Abanda CDP".
_TRAILING_DESCRIPTION = re.compile(
    r"\s+(?:city and borough|consolidated government|metropolitan government|unified government|metro government"
    r"|urban county|charter township|unorganized territory|city|town|township|village|borough|municipality"
    r"|plantation|CDP|CCD|UT|gore|grant|location|purchase|comunidad|zona urbana)$",
)
_LEADING_DESCRIPTION = re.compile(r"^(?:Town|City|Village|Borough) of\s+")
_BALANCE = re.compile(r"\s*\(balance\)$")


@dataclass(frozen=True)
class GazetteerEntry:
    """A named US place with its internal point coordinates."""

    key: str
    state: str
    name: str
    latitude: float
    longitude: float
    priority: int


def normalize_place_name(name: str) -> str:
    """Return a lookup key that is insensitive to case, punctuation, spacing and common abbreviations.

    >>> normalize_place_name("East St. Louis")
    'eastsaintlouis'
    >>> normalize_place_name("Mc Calla") == normalize_place_name("McCalla")
    True
    >>> normalize_place_name("De Forest") == normalize_place_name("DeForest")
    True
    >>> normalize_place_name("Canon City") == normalize_place_name("Cañon City")
    True
    """
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    words = re.sub(r"[^a-z0-9& ]", " ", ascii_name.lower().replace("'", "").replace(".", "")).split()
    return "".join(_ABBREVIATIONS.get(word, word) for word in words).replace("&", "and")


def clean_census_name(name: str) -> str:
    """Strip the Census legal description from a place name.

    >>> clean_census_name("Indianapolis city (balance)")
    'Indianapolis'
    >>> clean_census_name("Town of Pecos city")
    'Pecos'
    >>> clean_census_name("Carson City")
    'Carson City'
    """
    cleaned = _LEADING_DESCRIPTION.sub("", _BALANCE.sub("", name.strip()))
    previous = None
    while previous != cleaned:
        previous = cleaned
        cleaned = _TRAILING_DESCRIPTION.sub("", cleaned)
    return cleaned


def name_aliases(name: str) -> list[str]:
    """Return alternative short names a place is commonly called by.

    >>> name_aliases("Nashville-Davidson")
    ['Nashville']
    >>> name_aliases("Augusta-Richmond County")
    ['Augusta']
    >>> name_aliases("Boise City")
    ['Boise']
    """
    aliases = []
    first_part = re.split(r"[-/]", name)[0].strip()
    if first_part != name:
        aliases.append(first_part)
    if name.endswith(" City"):
        aliases.append(name.removesuffix(" City"))
    return aliases


def _read_census_file(path: Path) -> Iterator[dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        member = next(info for info in archive.infolist() if info.filename.endswith(".txt"))
        with archive.open(member) as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8"), delimiter="|")
            for row in reader:
                yield {key.strip(): value.strip() for key, value in row.items()}


def _entries_from_file(path: Path, exact_priority: int, alias_priority: int) -> Iterator[GazetteerEntry]:
    for row in _read_census_file(path):
        name = clean_census_name(row["NAME"])
        if not name:
            continue
        latitude, longitude = float(row["INTPTLAT"]), float(row["INTPTLONG"])
        for candidate, priority in [(name, exact_priority)] + [(alias, alias_priority) for alias in name_aliases(name)]:
            yield GazetteerEntry(
                key=normalize_place_name(candidate),
                state=row["USPS"],
                name=candidate,
                latitude=latitude,
                longitude=longitude,
                priority=priority,
            )


def _entries_from_overrides(path: Path) -> Iterator[GazetteerEntry]:
    with path.open(encoding="utf-8", newline="") as overrides:
        for row in csv.DictReader(overrides):
            yield GazetteerEntry(
                key=normalize_place_name(row["name"]),
                state=row["state"],
                name=row["name"],
                latitude=float(row["latitude"]),
                longitude=float(row["longitude"]),
                priority=PRIORITY_OVERRIDE,
            )


def build_gazetteer(
    places_path: Path,
    county_subdivisions_path: Path,
    overrides_path: Path | None = None,
) -> dict[tuple[str, str], GazetteerEntry]:
    """Build a ``(normalized name, state) -> entry`` index from the Census Gazetteer files.

    Places (cities, towns, CDPs) take precedence; county subdivisions fill in townships such as Mahwah, NJ;
    the optional overrides file (see the ``geocode_missing_places`` command) fills in the communities that
    the Census does not list at all.
    """
    entries = itertools.chain(
        _entries_from_file(places_path, PRIORITY_PLACE, PRIORITY_PLACE_ALIAS),
        _entries_from_file(county_subdivisions_path, PRIORITY_COUNTY_SUBDIVISION, PRIORITY_COUNTY_SUBDIVISION_ALIAS),
        _entries_from_overrides(overrides_path) if overrides_path and overrides_path.exists() else [],
    )
    index: dict[tuple[str, str], GazetteerEntry] = {}
    for entry in entries:
        lookup = (entry.key, entry.state)
        current = index.get(lookup)
        if current is None or entry.priority < current.priority:
            index[lookup] = entry
    return index
