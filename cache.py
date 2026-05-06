"""
Simple JSON cache for fetched InPost point data.

Fetching all Polish points takes ~2-3 minutes and thousands of API calls.
The cache saves the raw list to disk so subsequent runs are instant.
Use --refresh to force a new fetch.
"""

import json
import time
from pathlib import Path
from typing import Callable, Iterator

DEFAULT_CACHE_FILE = Path(".inpost_cache.json")
CACHE_TTL_SECONDS = 60 * 60 * 12  # 12 hours


def load_cache(path: Path = DEFAULT_CACHE_FILE) -> list[dict] | None:
    """Return cached points, or None if cache is missing / expired."""
    if not path.exists():
        return None

    try:
        with path.open(encoding="utf-8") as f:
            payload = json.load(f)

        age = time.time() - payload.get("saved_at", 0)
        if age > CACHE_TTL_SECONDS:
            return None

        return payload.get("items", [])
    except (json.JSONDecodeError, KeyError, OSError):
        return None


def save_cache(items: list[dict], path: Path = DEFAULT_CACHE_FILE) -> None:
    """Persist points to cache file."""
    payload = {"saved_at": time.time(), "items": items}
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)


def get_raw_points(
    fetch_fn: Callable[[], Iterator[dict]],
    refresh: bool = False,
    cache_path: Path = DEFAULT_CACHE_FILE,
    progress_callback: Callable[[int], None] | None = None,
) -> list[dict]:
    """
    Return raw point dicts from cache or fresh API fetch.

    Args:
        fetch_fn:          A callable that returns an iterator of raw API dicts.
        refresh:           If True, bypass the cache and re-fetch.
        cache_path:        Where to read/write the cache.
        progress_callback: Called with the running count after each API item (for progress bars).
    """
    if not refresh:
        cached = load_cache(cache_path)
        if cached is not None:
            return cached

    items: list[dict] = []
    for raw in fetch_fn():
        items.append(raw)
        if progress_callback:
            progress_callback(len(items))

    save_cache(items, cache_path)
    return items
