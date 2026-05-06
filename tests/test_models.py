"""Tests for point_from_dict parsing logic."""

import pytest
from inpost_scout.models import point_from_dict


RAW_VALID = {
    "name": "WAW01M",
    "type": "parcel_locker",
    "status": "Operating",
    "is_next_24h": True,
    "location": {"latitude": 52.2297, "longitude": 21.0122},
    "address": {
        "city": "Warszawa",
        "street": "Marszałkowska",
        "building_number": "1",
        "post_code": "00-624",
        "province": "mazowieckie",
        "line1": "ul. Marszałkowska 1",
        "line2": "00-624 Warszawa",
    },
    "functions": ["parcel_locker_only"],
    "operating_hours": "Pon-Nd: 00:00-24:00",
}


class TestPointFromDict:
    def test_parses_valid_point(self):
        point = point_from_dict(RAW_VALID)
        assert point is not None
        assert point.name == "WAW01M"
        assert point.is_next_24h is True
        assert point.address.city == "Warszawa"
        assert point.location.latitude == pytest.approx(52.2297)

    def test_returns_none_on_zero_coordinates(self):
        raw = {**RAW_VALID, "location": {"latitude": 0, "longitude": 0}}
        assert point_from_dict(raw) is None

    def test_handles_missing_address_gracefully(self):
        raw = {**RAW_VALID, "address": {}}
        point = point_from_dict(raw)
        assert point is not None
        assert point.address.city == ""

    def test_handles_none_functions(self):
        raw = {**RAW_VALID, "functions": None}
        point = point_from_dict(raw)
        assert point is not None
        assert point.functions == []

    def test_is_operating_true_for_operating_status(self):
        point = point_from_dict(RAW_VALID)
        assert point.is_operating is True

    def test_is_operating_false_for_blocked_status(self):
        raw = {**RAW_VALID, "status": "Zablokowany"}
        point = point_from_dict(raw)
        assert point is not None
        assert point.is_operating is False

    def test_city_normalized_is_lowercase(self):
        point = point_from_dict(RAW_VALID)
        assert point.city_normalized == "warszawa"
