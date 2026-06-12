from __future__ import annotations
import math
from typing import Iterable

EARTH_RADIUS_KM = 6371.0088
KM_PER_NM = 1.852


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def initial_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlambda = math.radians(lon2 - lon1)
    y = math.sin(dlambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlambda)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def km_to_nm(km: float) -> float:
    return km / KM_PER_NM


def implied_speed_knots(lat1: float, lon1: float, t1, lat2: float, lon2: float, t2) -> float:
    hours = abs((t2 - t1).total_seconds()) / 3600
    if hours <= 0:
        return float("inf")
    return km_to_nm(haversine_km(lat1, lon1, lat2, lon2)) / hours


def bounds(points: Iterable[tuple[float, float]]) -> dict[str, float]:
    pts = list(points)
    if not pts:
        return {"min_lat": 0, "max_lat": 0, "min_lon": 0, "max_lon": 0}
    lats = [p[0] for p in pts]
    lons = [p[1] for p in pts]
    return {"min_lat": min(lats), "max_lat": max(lats), "min_lon": min(lons), "max_lon": max(lons)}
