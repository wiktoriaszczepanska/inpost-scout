"""
Data models for InPost points.
Typed dataclasses make the rest of the code easier to read and less error-prone.
"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Location:
    latitude: float
    longitude: float


@dataclass
class Address:
    city: str
    street: str
    building_number: str
    post_code: str
    province: str
    line1: str  # human-readable first line, e.g. "ul. Marszałkowska 1"
    line2: str  # human-readable second line, e.g. "00-001 Warszawa"


@dataclass
class Point:
    name: str              # locker ID, e.g. "WAW01M"
    type: str              # e.g. "parcel_locker", "pok", ...
    status: str            # e.g. "Operating", "Zablokowany"
    is_next_24h: bool      # true if available 24/7
    location: Location
    address: Address
    functions: list[str] = field(default_factory=list)
    operating_hours: str = ""

    @property
    def is_operating(self) -> bool:
        return self.status.lower() in {"operating", "działa"}

    @property
    def city_normalized(self) -> str:
        """Lowercase, stripped city name for reliable comparisons."""
        return self.address.city.strip().lower()


def point_from_dict(raw: dict) -> Point | None:
    """
    Build a Point from a raw API response dict.
    Returns None if the raw data is missing critical fields.
    """
    try:
        loc = raw.get("location") or {}
        addr = raw.get("address") or {}
        addr_details = raw.get("address_details") or {}

        location = Location(
            latitude=float(loc.get("latitude", 0)),
            longitude=float(loc.get("longitude", 0)),
        )

        address = Address(
            city=addr.get("city") or addr_details.get("city", ""),
            street=addr.get("street") or addr_details.get("street", ""),
            building_number=addr.get("building_number") or addr_details.get("building_number", ""),
            post_code=addr.get("post_code") or addr_details.get("post_code", ""),
            province=addr.get("province") or addr_details.get("province", ""),
            line1=addr.get("line1", ""),
            line2=addr.get("line2", ""),
        )

        # Skip points with no valid coordinates
        if location.latitude == 0 and location.longitude == 0:
            return None

        return Point(
            name=raw.get("name", ""),
            type=raw.get("type", ""),
            status=raw.get("status", ""),
            is_next_24h=bool(raw.get("is_next_24h", False)),
            location=location,
            address=address,
            functions=raw.get("functions") or [],
            operating_hours=raw.get("operating_hours") or "",
        )
    except (TypeError, ValueError, KeyError):
        return None
