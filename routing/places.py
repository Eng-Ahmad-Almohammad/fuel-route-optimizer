"""Resolve the API's "City, ST" inputs to places with coordinates, without calling a geocoding service."""

import re

from stations.gazetteer import normalize_place_name
from stations.models import Place

_CITY_STATE = re.compile(r"^\s*(?P<city>[^,]+?)\s*,\s*(?P<state>[A-Za-z]{2})\s*$")


class PlaceNotFoundError(ValueError):
    """The text is not a known US "City, ST"."""


def resolve_place(text: str) -> Place:
    """Look up a "City, ST" string such as "Big Cabin, OK" in the Place table."""
    match = _CITY_STATE.match(text)
    if match is None:
        raise PlaceNotFoundError(f'"{text}" is not in "City, ST" format, e.g. "Chicago, IL".')
    city, state = match["city"], match["state"].upper()
    place = Place.objects.filter(key=normalize_place_name(city), state=state).first()
    if place is None:
        raise PlaceNotFoundError(f'Unknown US place "{city}, {state}".')
    return place
