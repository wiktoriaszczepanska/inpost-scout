"""
Analytics over a list of Point objects.
Pure functions — no side effects, easy to test.
"""

from __future__ import annotations
from collections import Counter, defaultdict
from dataclasses import dataclass

from .models import Point


@dataclass
class CityStats:
    city: str
    total: int
    open_24h: int
    operating: int
    types: dict[str, int]


def points_by_city(points: list[Point]) -> dict[str, list[Point]]:
    """Group points by normalised city name."""
    grouped: dict[str, list[Point]] = defaultdict(list)
    for p in points:
        grouped[p.city_normalized].append(p)
    return dict(grouped)


def city_stats(points: list[Point]) -> list[CityStats]:
    """
    Return a list of CityStats sorted by total point count (descending).
    Useful for the 'stats' CLI command and the analytics panel.
    """
    grouped = points_by_city(points)
    result = []

    for city_key, city_points in grouped.items():
        display_name = city_points[0].address.city  # original casing
        type_counter = Counter(p.type for p in city_points)

        result.append(
            CityStats(
                city=display_name,
                total=len(city_points),
                open_24h=sum(1 for p in city_points if p.is_next_24h),
                operating=sum(1 for p in city_points if p.is_operating),
                types=dict(type_counter),
            )
        )

    return sorted(result, key=lambda s: s.total, reverse=True)


def filter_points(
    points: list[Point],
    city: str | None = None,
    open_24h_only: bool = False,
    operating_only: bool = True,
    type_filter: str | None = None,
    function_filter: str | None = None,
) -> list[Point]:
    """
    Filter points by various criteria.
    All filters are AND-combined.
    """
    result = points

    if city:
        city_lower = city.strip().lower()
        result = [p for p in result if city_lower in p.city_normalized]

    if open_24h_only:
        result = [p for p in result if p.is_next_24h]

    if operating_only:
        result = [p for p in result if p.is_operating]

    if type_filter:
        result = [p for p in result if type_filter.lower() in p.type.lower()]

    if function_filter:
        result = [
            p for p in result
            if any(function_filter.lower() in f.lower() for f in p.functions)
        ]

    return result


def nearest_points(
    points: list[Point],
    lat: float,
    lon: float,
    limit: int = 10,
) -> list[tuple[float, Point]]:
    """
    Return the `limit` closest points to (lat, lon) sorted by distance.
    Uses the Haversine formula for accuracy.
    """
    import math

    def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371.0  # Earth radius in km
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return R * 2 * math.asin(math.sqrt(a))

    with_dist = [
        (haversine(lat, lon, p.location.latitude, p.location.longitude), p)
        for p in points
    ]
    return sorted(with_dist, key=lambda x: x[0])[:limit]


def overall_summary(points: list[Point]) -> dict:
    """High-level summary dict for display in the stats command."""
    cities = points_by_city(points)
    type_counter = Counter(p.type for p in points)
    return {
        "total_points": len(points),
        "cities_covered": len(cities),
        "open_24h": sum(1 for p in points if p.is_next_24h),
        "operating": sum(1 for p in points if p.is_operating),
        "types": dict(type_counter),
    }
