"""Distance helpers on the Earth's surface.

Coordinates follow the GeoJSON convention used by the routing API: ``(longitude, latitude)`` in degrees.
"""

import math

EARTH_RADIUS_MILES = 3958.8
MILES_PER_DEGREE_LATITUDE = math.pi * EARTH_RADIUS_MILES / 180

LonLat = tuple[float, float]


def haversine_miles(a: LonLat, b: LonLat) -> float:
    """Return the great-circle distance between two points in miles.

    >>> round(haversine_miles((-74.006, 40.7128), (-118.2437, 34.0522)))
    2446
    """
    lon1, lat1, lon2, lat2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(h))


def approx_miles(a: LonLat, b: LonLat) -> float:
    """Return a fast flat-Earth approximation of the distance in miles, accurate to well under 1% within ~50 miles.

    >>> round(approx_miles((-95.23, 36.54), (-95.23, 36.64)), 2)
    6.91
    """
    mean_latitude = math.radians((a[1] + b[1]) / 2)
    dx = (b[0] - a[0]) * math.cos(mean_latitude)
    dy = b[1] - a[1]
    return MILES_PER_DEGREE_LATITUDE * math.hypot(dx, dy)
