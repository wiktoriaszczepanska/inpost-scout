"""
Tests for the analyzer module.
Run with: pytest tests/ -v
"""

import pytest
from inpost_scout.models import Point, Location, Address
from inpost_scout.analyzer import (
    city_stats,
    filter_points,
    nearest_points,
    overall_summary,
)


# ─── fixtures ─────────────────────────────────────────────────────────────────

def make_point(
    name: str = "TEST01",
    city: str = "Warszawa",
    lat: float = 52.22,
    lon: float = 21.01,
    is_next_24h: bool = True,
    status: str = "Operating",
    point_type: str = "parcel_locker",
    functions: list[str] | None = None,
) -> Point:
    return Point(
        name=name,
        type=point_type,
        status=status,
        is_next_24h=is_next_24h,
        location=Location(latitude=lat, longitude=lon),
        address=Address(
            city=city,
            street="Testowa",
            building_number="1",
            post_code="00-001",
            province="mazowieckie",
            line1="ul. Testowa 1",
            line2=f"00-001 {city}",
        ),
        functions=functions or [],
    )


SAMPLE_POINTS = [
    make_point("WAW01", "Warszawa", lat=52.22, lon=21.01, is_next_24h=True),
    make_point("WAW02", "Warszawa", lat=52.23, lon=21.02, is_next_24h=False),
    make_point("WAW03", "Warszawa", lat=52.21, lon=21.00, status="Zablokowany"),
    make_point("KRK01", "Kraków",   lat=50.06, lon=19.94, is_next_24h=True),
    make_point("KRK02", "Kraków",   lat=50.07, lon=19.95, point_type="pok"),
    make_point("GDN01", "Gdańsk",   lat=54.35, lon=18.65, is_next_24h=True),
]


# ─── filter_points ────────────────────────────────────────────────────────────

class TestFilterPoints:
    def test_no_filters_returns_operating_only_by_default(self):
        results = filter_points(SAMPLE_POINTS)
        assert all(p.is_operating for p in results)
        assert len(results) == 5  # WAW03 is blocked

    def test_city_filter_case_insensitive(self):
        results = filter_points(SAMPLE_POINTS, city="kraków")
        assert len(results) == 2
        assert all(p.city_normalized == "kraków" for p in results)

    def test_city_partial_match(self):
        results = filter_points(SAMPLE_POINTS, city="gdań")
        assert len(results) == 1
        assert results[0].name == "GDN01"

    def test_open_24h_filter(self):
        results = filter_points(SAMPLE_POINTS, open_24h_only=True)
        assert all(p.is_next_24h for p in results)

    def test_type_filter(self):
        results = filter_points(SAMPLE_POINTS, type_filter="pok", operating_only=False)
        assert all("pok" in p.type for p in results)
        assert len(results) == 1

    def test_combined_city_and_24h(self):
        results = filter_points(SAMPLE_POINTS, city="Warszawa", open_24h_only=True)
        assert len(results) == 1
        assert results[0].name == "WAW01"

    def test_empty_input_returns_empty(self):
        assert filter_points([]) == []

    def test_city_no_match_returns_empty(self):
        results = filter_points(SAMPLE_POINTS, city="Wrocław")
        assert results == []


# ─── city_stats ───────────────────────────────────────────────────────────────

class TestCityStats:
    def test_sorted_by_total_descending(self):
        stats = city_stats(SAMPLE_POINTS)
        totals = [s.total for s in stats]
        assert totals == sorted(totals, reverse=True)

    def test_correct_city_count(self):
        stats = city_stats(SAMPLE_POINTS)
        assert len(stats) == 3  # Warszawa, Kraków, Gdańsk

    def test_warszawa_stats(self):
        stats = city_stats(SAMPLE_POINTS)
        waw = next(s for s in stats if s.city == "Warszawa")
        assert waw.total == 3
        assert waw.open_24h == 2  # WAW01 + WAW03 (both default to 24h=True)
        assert waw.operating == 2  # one is blocked

    def test_empty_input(self):
        assert city_stats([]) == []


# ─── nearest_points ───────────────────────────────────────────────────────────

class TestNearestPoints:
    def test_returns_correct_limit(self):
        results = nearest_points(SAMPLE_POINTS, lat=52.22, lon=21.01, limit=3)
        assert len(results) == 3

    def test_closest_is_first(self):
        results = nearest_points(SAMPLE_POINTS, lat=52.22, lon=21.01, limit=6)
        distances = [d for d, _ in results]
        assert distances == sorted(distances)

    def test_nearest_to_warsaw_centre_is_warsaw_point(self):
        results = nearest_points(SAMPLE_POINTS, lat=52.22, lon=21.01, limit=1)
        _, point = results[0]
        assert point.city_normalized == "warszawa"

    def test_limit_larger_than_pool(self):
        results = nearest_points(SAMPLE_POINTS, lat=52.22, lon=21.01, limit=100)
        assert len(results) == len(SAMPLE_POINTS)


# ─── overall_summary ──────────────────────────────────────────────────────────

class TestOverallSummary:
    def test_total_count(self):
        summary = overall_summary(SAMPLE_POINTS)
        assert summary["total_points"] == len(SAMPLE_POINTS)

    def test_cities_covered(self):
        summary = overall_summary(SAMPLE_POINTS)
        assert summary["cities_covered"] == 3

    def test_open_24h_count(self):
        summary = overall_summary(SAMPLE_POINTS)
        assert summary["open_24h"] == 5  # all except WAW02

    def test_types_present(self):
        summary = overall_summary(SAMPLE_POINTS)
        assert "parcel_locker" in summary["types"]
        assert "pok" in summary["types"]
