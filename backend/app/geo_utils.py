"""Great-circle distance helpers.

These replace PostGIS ``ST_Distance`` calls when running on SQLite.  When the
Postgres backend is enabled the same function signatures are used, so callers in
the engine modules never branch on the database backend.
"""

from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_M = 6_371_008.8


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres between two WGS-84 points."""
    p1, p2 = radians(lat1), radians(lat2)
    d_lat = p2 - p1
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat / 2) ** 2 + cos(p1) * cos(p2) * sin(d_lon / 2) ** 2
    return 2 * EARTH_RADIUS_M * asin(sqrt(a))
