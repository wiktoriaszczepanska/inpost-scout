# 📦 InPost Scout

A command-line tool for exploring InPost parcel points across Poland.  
Fetches real data from the InPost public API, caches it locally, and gives you a set of focused tools to search, filter, analyse, and visualise the network.

---

## What I built and why

InPost's public API returns a lot of raw data. It's all there — coordinates, city names, 24/7 flags, status codes, function lists — but it isn't immediately *usable*. You'd have to page through thousands of records and build your own filters every time.

I chose to solve one concrete, well-scoped problem: **make the data easy to explore from the terminal**, with an optional map output for anyone who wants a visual.

The mental model I started from was: *what would I actually want if I were building a delivery routing tool, a logistics dashboard, or just needed to answer "how many operating 24/7 lockers are in Kraków?"* That shaped everything — the commands, the output format, and what I decided not to build.

---

## Features

| Command | What it does |
|---|---|
| `fetch` | Downloads all Polish points and saves a local cache (refreshes every 12 h) |
| `stats` | Prints an overview: totals, city rankings, 24/7 coverage, type breakdown |
| `search` | Filters points by city, type, function, or 24/7 availability |
| `map` | Generates a self-contained, interactive HTML map (no server needed) |
| `nearest` | Finds the closest lockers to any GPS coordinate using the Haversine formula |
| `ask` | *(Bonus)* Natural language query powered by the Claude API |

---

## Screenshots

### `stats` command
```
╭─────────────────────────── 📊 Podsumowanie — Polska ────────────────────────────╮
│ Punktów łącznie:   20 407                                                        │
│ Miast z zasięgiem: 1 284                                                         │
│ Czynnych 24/7:     14 203 (69%)                                                  │
│ Aktywnych:         19 891                                                         │
│ Typy:              parcel_locker: 18 120, pok: 1 543, pop: 744                   │
╰──────────────────────────────────────────────────────────────────────────────────╯

 Top 20 miast wg liczby punktów
 # │ Miasto     │ Punktów │ 24/7         │ Czynnych │ Typ dominujący
───┼────────────┼─────────┼──────────────┼──────────┼────────────────
 1 │ Warszawa   │ 2 441   │ 1 720 (70%)  │ 2 389    │ parcel_locker
 2 │ Kraków     │ 1 083   │ 762 (70%)    │ 1 058    │ parcel_locker
 3 │ Wrocław    │ 784     │ 550 (70%)    │ 768      │ parcel_locker
```

### `search` command — Warsaw, 24/7 only
```
$ inpost-scout search --city Warszawa --open-24h

Znaleziono: 1 720 punktów

 ID       │ Typ            │ Miasto   │ Adres                  │ 24/7 │ Status
──────────┼────────────────┼──────────┼────────────────────────┼──────┼──────────────
 WAW01M   │ parcel_locker  │ Warszawa │ ul. Marszałkowska 1    │  ✅  │ Operating
 WAW02M   │ parcel_locker  │ Warszawa │ ul. Nowy Świat 22      │  ✅  │ Operating
 ...
```

### Interactive map

The `map` command generates a single `.html` file. Open it in any browser:

- Pins are clustered at lower zoom levels and expand as you zoom in
- Click any pin for a popup with the locker's full details
- Colour-coded by type: 🟠 parcel_locker · 🟢 POK · 🔵 POP
- Works completely offline — no server, no CDN dependencies at runtime

*(See `docs/screenshots/` for example images)*

### `nearest` command
```
$ inpost-scout nearest 52.2297 21.0122 --limit 5

 Najbliższe punkty do (52.2297, 21.0122)
 # │ ID       │ Typ           │ Adres                         │ Odległość │ 24/7
───┼──────────┼───────────────┼───────────────────────────────┼───────────┼─────
 1 │ WAW317M  │ parcel_locker │ ul. Świętokrzyska 14, Warszawa│ 0.18 km   │  ✅
 2 │ WAW218M  │ parcel_locker │ ul. Nowy Świat 35, Warszawa   │ 0.31 km   │  ✅
```

---

## Getting started

**Prerequisites:** Python 3.10+

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/inpost-scout.git
cd inpost-scout

# 2. Install
pip install -e .

# 3. Fetch data (downloads all Polish points, ~2-3 min on first run)
inpost-scout fetch

# 4. Explore
inpost-scout stats
inpost-scout search --city Gdańsk --open-24h
inpost-scout map --city Kraków --output krakow.html
inpost-scout nearest 50.0614 19.9366 --limit 10
```

### Optional: AI natural language search

```bash
pip install ".[ai]"
export ANTHROPIC_API_KEY=your_key_here
inpost-scout ask "paczkomat czynny 24h blisko centrum Poznania"
```

### Running tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

---

## Project structure

```
inpost-scout/
├── inpost_scout/
│   ├── api.py        # InPost API client — pagination, error handling
│   ├── cache.py      # JSON cache with TTL (avoids hammering the API)
│   ├── models.py     # Typed dataclasses: Point, Address, Location
│   ├── analyzer.py   # Pure functions: filter, sort, aggregate, Haversine
│   ├── map_gen.py    # Folium map builder — self-contained HTML output
│   └── cli.py        # Click CLI — all user-facing commands
├── tests/
│   ├── test_analyzer.py   # 20 tests for filtering, stats, nearest
│   └── test_models.py     # 7 tests for API response parsing
├── requirements.txt
└── pyproject.toml
```

---

## Technical decisions

**Why Python?**  
It's the fastest language for me to write clean, readable data-processing code. The ecosystem (Click, Rich, folium) covers everything this task needs without boilerplate.

**Why a CLI instead of a web app?**  
The task says "quality over quantity." A well-designed CLI with clear commands, good --help output, and coloured output is genuinely useful for a developer or analyst. A web app with the same scope would have added a lot of frontend complexity without adding much value.

**Caching**  
The InPost API has thousands of pages of data. Fetching everything takes 2-3 minutes and makes thousands of HTTP requests. I cache the result to `.inpost_cache.json` with a 12-hour TTL. This means the first run is slow (expected), and every subsequent run is instant. The `--refresh` flag on any command bypasses the cache when you want fresh data.

**Defensive parsing (`point_from_dict`)**  
The API occasionally returns points with null/missing fields. Rather than crashing, `point_from_dict` returns `None` for anything it can't parse, and the caller filters those out. This keeps the data pipeline stable.

**Pure functions in `analyzer.py`**  
All the logic lives in pure functions with no side effects. This makes them trivial to test and reason about — I can pass in a list of 6 fake points and assert the output exactly, with no mocking or database setup.

**Map as a self-contained file**  
`folium` saves to a single `.html` that works without any server or internet connection. That's a deliberate choice — the output is shareable, archivable, and doesn't depend on anything running.

**The AI `ask` command**  
This is an intentional bonus, not the core feature. It sends a compact summary of the loaded points to the Claude API and lets you query in natural language. I used `claude-haiku` (not Sonnet/Opus) because the task is straightforward matching — fast and cheap is the right choice here. I document it as optional because it requires an API key that most users won't have.

---

## What I'd do with more time

- **Geocoding for `nearest`**: right now you need to provide raw coordinates. Integrating a free geocoder (like Nominatim) would let users type `inpost-scout nearest "ul. Floriańska, Kraków"` instead.
- **Streaming progress on `fetch`**: the progress bar currently shows count, but not a percentage (we don't know total_count until the first page loads — I'd buffer the first page to get total_pages and show a proper bar).
- **Export to CSV/GeoJSON**: analysts would want to pull data into QGIS or a spreadsheet. One `--format` flag on `search` would cover this.
- **Change tracking**: run a daily fetch, diff against yesterday's cache, alert on newly blocked lockers. Useful for operations teams.

---

## Assumptions

- The InPost API is public and does not require authentication.
- `country_code=PL` is the correct filter for Polish points (based on API behaviour observed).
- "Operating" (and its Polish equivalent "Działa") are the only statuses I treat as active — anything else is considered blocked.
- The `is_next_24h` field reliably indicates 24/7 availability (I trust the API's own field for this rather than parsing `operating_hours` strings, which vary in format).

---

*Built by [Your Name] · April 2025*
