"""
InPost API client.
Handles pagination and basic error handling when fetching points from the public API.
"""

import time
import requests
from typing import Iterator

BASE_URL = "https://api-global-points.easypack24.net/v1/points"
DEFAULT_PER_PAGE = 100
REQUEST_DELAY = 0.05  # seconds between pages — polite to the API


def fetch_all_points(
    country_code: str = "PL",
    per_page: int = DEFAULT_PER_PAGE,
    max_pages: int | None = None,
) -> Iterator[dict]:
    """
    Yield every point returned by the InPost API for a given country.

    Args:
        country_code: ISO country code to filter by (default: "PL").
        per_page: Number of results per page (max supported by the API is 100).
        max_pages: If set, stop after this many pages (useful for quick demos).

    Yields:
        Raw point dicts as returned by the API.
    """
    page = 1
    total_pages = None

    while True:
        params = {
            "country_code": country_code,
            "per_page": per_page,
            "page": page,
        }

        try:
            response = requests.get(BASE_URL, params=params, timeout=15)
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            raise RuntimeError(
                f"InPost API returned an error on page {page}: {exc}"
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise RuntimeError(
                "Could not reach the InPost API. Check your internet connection."
            ) from exc

        data = response.json()

        # Capture total page count from first response
        if total_pages is None:
            total_pages = data.get("total_pages", 1)

        items = data.get("items", [])
        if not items:
            break

        yield from items

        if page >= total_pages:
            break
        if max_pages is not None and page >= max_pages:
            break

        page += 1
        time.sleep(REQUEST_DELAY)
