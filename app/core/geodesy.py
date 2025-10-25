import math
from typing import Iterable, List, Sequence, Tuple

EARTH_RADIUS_KM = 6371.0088

PointTuple = Tuple[float, float]

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon pairs."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c

def batch_haversine_km(points: Sequence[PointTuple], other: PointTuple) -> List[float]:
    return [haversine_km(lat, lon, other[0], other[1]) for lat, lon in points]

def bearing_degrees(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the initial bearing from point A to point B in degrees."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dlambda = math.radians(lon2 - lon1)
    x = math.sin(dlambda) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlambda)
    brng = math.degrees(math.atan2(x, y))
    return (brng + 360) % 360

def destination_point(lat: float, lon: float, bearing_deg: float, distance_km: float) -> PointTuple:
    """Project a point from lat/lon using a bearing (deg) and distance (km)."""
    angular_distance = distance_km / EARTH_RADIUS_KM
    bearing = math.radians(bearing_deg)
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)

    new_lat = math.asin(
        math.sin(lat_rad) * math.cos(angular_distance)
        + math.cos(lat_rad) * math.sin(angular_distance) * math.cos(bearing)
    )
    new_lon = lon_rad + math.atan2(
        math.sin(bearing) * math.sin(angular_distance) * math.cos(lat_rad),
        math.cos(angular_distance) - math.sin(lat_rad) * math.sin(new_lat),
    )
    return math.degrees(new_lat), (math.degrees(new_lon) + 540) % 360 - 180

def distance_matrix(origins: Iterable[PointTuple], destinations: Iterable[PointTuple]) -> List[List[float]]:
    dest_list = list(destinations)
    result: List[List[float]] = []
    for origin in origins:
        row = [haversine_km(origin[0], origin[1], dest[0], dest[1]) for dest in dest_list]
        result.append(row)
    return result
