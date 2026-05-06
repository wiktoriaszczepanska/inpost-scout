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

        if location.latitude == 0 and location.longitude == 0:
            return None

        # type bywa listą lub stringiem
        raw_type = raw.get("type", "")
        if isinstance(raw_type, list):
            point_type = ", ".join(raw_type) if raw_type else ""
        else:
            point_type = raw_type or ""

        # 24/7 — API używa różnych nazw pola
        is_24h = bool(
            raw.get("is_next_24h")
            or raw.get("is24h")
            or raw.get("open_24h")
            or raw.get("247")
        )

        # filtr kraju po kodzie pocztowym (API nie filtruje idealnie)
        post_code = address.post_code or ""
        country = raw.get("country_code") or raw.get("country") or ""
        if country and country.upper() not in ("PL", ""):
            return None

        return Point(
            name=raw.get("name", ""),
            type=point_type,
            status=raw.get("status", ""),
            is_next_24h=is_24h,
            location=location,
            address=address,
            functions=raw.get("functions") or [],
            operating_hours=raw.get("operating_hours") or "",
        )
    except (TypeError, ValueError, KeyError):
        return None

