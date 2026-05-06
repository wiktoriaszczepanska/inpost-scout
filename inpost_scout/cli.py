"""
InPost Scout CLI.

Commands:
  fetch    Download and cache all Polish InPost points
  map      Generate an interactive HTML map
  search   Filter and list matching points
  stats    Show analytics (top cities, coverage, type breakdown)
  nearest  Find the closest lockers to given coordinates
  ask      (Bonus) Natural language query via Claude API
"""

import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich import print as rprint

from .api import fetch_all_points
from .cache import get_raw_points, DEFAULT_CACHE_FILE
from .models import point_from_dict, Point
from .analyzer import city_stats, filter_points, nearest_points, overall_summary
from .map_gen import generate_map

console = Console()


# ─── helpers ──────────────────────────────────────────────────────────────────

def _load_points(refresh: bool = False, max_pages: int | None = None) -> list[Point]:
    """Load points from cache or API, parse into Point objects."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Ładowanie punktów InPost…", total=None)
        count_holder = [0]

        def on_progress(n: int) -> None:
            count_holder[0] = n
            progress.update(task, description=f"Pobieranie… ({n:,} punktów)")

        raw_items = get_raw_points(
            fetch_fn=lambda: fetch_all_points(country_code="PL", max_pages=max_pages),
            refresh=refresh,
            progress_callback=on_progress if refresh else None,
        )

    points = [p for raw in raw_items if (p := point_from_dict(raw)) is not None]
    return points


# ─── CLI group ────────────────────────────────────────────────────────────────

@click.group()
@click.version_option("1.0.0", prog_name="InPost Scout")
def cli():
    """
    \b
    📦 InPost Scout — narzędzie do eksploracji paczekomatów InPost w Polsce.

    Zacznij od:
      inpost-scout fetch       # pobierz dane (zapisuje cache na 12h)
      inpost-scout stats       # statystyki ogólne
      inpost-scout map         # wygeneruj mapę HTML
      inpost-scout search      # filtruj punkty
      inpost-scout nearest     # znajdź najbliższe
    """


# ─── fetch ────────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--refresh", is_flag=True, help="Ignoruj cache, pobierz od nowa.")
@click.option("--max-pages", default=None, type=int, help="Limit stron (do testów).")
def fetch(refresh: bool, max_pages: int | None):
    """Pobierz wszystkie polskie punkty InPost i zapisz do cache."""
    points = _load_points(refresh=True, max_pages=max_pages)
    console.print(
        Panel(
            f"[bold green]✓[/bold green] Pobrano [bold]{len(points):,}[/bold] punktów.\n"
            f"Cache zapisany w: [dim]{DEFAULT_CACHE_FILE}[/dim]",
            title="InPost Scout — fetch",
            border_style="green",
        )
    )


# ─── stats ────────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--top", default=20, show_default=True, help="Ile miast pokazać.")
@click.option("--refresh", is_flag=True, help="Ignoruj cache.")
def stats(top: int, refresh: bool):
    """Statystyki: liczba punktów na miasto, pokrycie 24/7, typy."""
    points = _load_points(refresh=refresh)
    summary = overall_summary(points)

    console.print(
        Panel(
            f"[bold]Punktów łącznie:[/bold]   {summary['total_points']:,}\n"
            f"[bold]Miast z zasięgiem:[/bold] {summary['cities_covered']:,}\n"
            f"[bold]Czynnych 24/7:[/bold]     {summary['open_24h']:,} "
            f"({100*summary['open_24h']//summary['total_points']}%)\n"
            f"[bold]Aktywnych:[/bold]         {summary['operating']:,}\n"
            f"[bold]Typy:[/bold]              "
            + ", ".join(f"{t}: {n:,}" for t, n in sorted(summary["types"].items(), key=lambda x: -x[1])),
            title="📊 Podsumowanie — Polska",
            border_style="cyan",
        )
    )

    table = Table(
        title=f"Top {top} miast wg liczby punktów",
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Miasto", min_width=16)
    table.add_column("Punktów", justify="right")
    table.add_column("24/7", justify="right")
    table.add_column("Czynnych", justify="right")
    table.add_column("Typ dominujący")

    for i, stat in enumerate(city_stats(points)[:top], 1):
        dominant_type = max(stat.types, key=stat.types.get) if stat.types else "—"
        pct_24h = int(100 * stat.open_24h / stat.total) if stat.total else 0
        table.add_row(
            str(i),
            stat.city,
            f"{stat.total:,}",
            f"{stat.open_24h:,} ({pct_24h}%)",
            f"{stat.operating:,}",
            dominant_type,
        )

    console.print(table)


# ─── search ───────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--city", "-c", default=None, help="Filtruj po nazwie miasta.")
@click.option("--open-24h", is_flag=True, help="Tylko punkty czynne 24/7.")
@click.option("--type", "type_filter", default=None, help="Filtruj po typie (np. parcel_locker).")
@click.option("--function", "function_filter", default=None, help="Wymagana funkcja punktu.")
@click.option("--limit", default=30, show_default=True, help="Max wyników.")
@click.option("--refresh", is_flag=True)
def search(city, open_24h, type_filter, function_filter, limit, refresh):
    """Wyszukaj punkty według kryteriów."""
    points = _load_points(refresh=refresh)
    results = filter_points(
        points,
        city=city,
        open_24h_only=open_24h,
        type_filter=type_filter,
        function_filter=function_filter,
    )

    console.print(f"[bold cyan]Znaleziono: {len(results):,} punktów[/bold cyan]")

    if not results:
        console.print("[yellow]Brak wyników dla podanych kryteriów.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold", border_style="dim")
    table.add_column("ID", min_width=8)
    table.add_column("Typ")
    table.add_column("Miasto")
    table.add_column("Adres")
    table.add_column("24/7")
    table.add_column("Status")

    for p in results[:limit]:
        table.add_row(
            p.name,
            p.type,
            p.address.city,
            p.address.line1,
            "✅" if p.is_next_24h else "❌",
            f"[green]{p.status}[/green]" if p.is_operating else f"[red]{p.status}[/red]",
        )

    console.print(table)
    if len(results) > limit:
        console.print(f"[dim]… i {len(results) - limit:,} więcej. Użyj --limit aby zobaczyć więcej.[/dim]")


# ─── map ──────────────────────────────────────────────────────────────────────

@cli.command("map")
@click.option("--city", "-c", default=None, help="Ogranicz mapę do jednego miasta.")
@click.option("--open-24h", is_flag=True, help="Pokaż tylko punkty 24/7.")
@click.option("--output", "-o", default="inpost_map.html", show_default=True)
@click.option("--refresh", is_flag=True)
def map_cmd(city, open_24h, output, refresh):
    """Wygeneruj interaktywną mapę HTML."""
    points = _load_points(refresh=refresh)
    filtered = filter_points(points, city=city, open_24h_only=open_24h)

    if not filtered:
        console.print("[red]Brak punktów do wyświetlenia po zastosowaniu filtrów.[/red]")
        sys.exit(1)

    title_parts = ["InPost Scout"]
    if city:
        title_parts.append(city.title())
    if open_24h:
        title_parts.append("24/7 only")

    out_path = Path(output)
    console.print(f"Generowanie mapy dla [bold]{len(filtered):,}[/bold] punktów…")
    result = generate_map(filtered, output_path=out_path, title=" — ".join(title_parts))
    console.print(f"[bold green]✓[/bold green] Mapa zapisana: [bold]{result}[/bold]")
    console.print("[dim]Otwórz plik w przeglądarce, by zobaczyć mapę.[/dim]")


# ─── nearest ──────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("lat", type=float)
@click.argument("lon", type=float)
@click.option("--limit", "-n", default=5, show_default=True)
@click.option("--open-24h", is_flag=True)
@click.option("--refresh", is_flag=True)
def nearest(lat, lon, limit, open_24h, refresh):
    """
    Znajdź najbliższe punkty do podanych współrzędnych.

    Przykład: inpost-scout nearest 52.2297 21.0122
    """
    points = _load_points(refresh=refresh)
    pool = filter_points(points, open_24h_only=open_24h)
    results = nearest_points(pool, lat, lon, limit=limit)

    table = Table(
        title=f"Najbliższe punkty do ({lat}, {lon})",
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("ID")
    table.add_column("Typ")
    table.add_column("Adres")
    table.add_column("Odległość", justify="right")
    table.add_column("24/7")

    for i, (dist_km, point) in enumerate(results, 1):
        dist_str = f"{dist_km:.2f} km" if dist_km >= 0.1 else f"{dist_km*1000:.0f} m"
        table.add_row(
            str(i),
            point.name,
            point.type,
            f"{point.address.line1}, {point.address.city}",
            dist_str,
            "✅" if point.is_next_24h else "❌",
        )

    console.print(table)


# ─── ask (bonus: Claude API) ──────────────────────────────────────────────────

@cli.command()
@click.argument("query")
@click.option("--city", "-c", default=None, help="Ogranicz do miasta przed zapytaniem.")
@click.option("--refresh", is_flag=True)
def ask(query: str, city: str | None, refresh: bool):
    """
    [Bonus] Zapytaj o paczkomat w języku naturalnym (wymaga ANTHROPIC_API_KEY).

    Przykład: inpost-scout ask "paczkomat czynny 24h w centrum Warszawy"
    """
    try:
        import anthropic
    except ImportError:
        console.print("[red]Zainstaluj anthropic: pip install anthropic[/red]")
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[red]Ustaw zmienną ANTHROPIC_API_KEY w środowisku.[/red]")
        sys.exit(1)

    points = _load_points(refresh=refresh)
    pool = filter_points(points, city=city)

    # Build a compact summary of available data to send to Claude
    sample_size = min(len(pool), 200)
    sample = pool[:sample_size]
    sample_text = "\n".join(
        f"{p.name} | {p.type} | {p.address.city} | {p.address.line1} | "
        f"24h={'tak' if p.is_next_24h else 'nie'} | status={p.status} | functions={','.join(p.functions)}"
        for p in sample
    )

    system_prompt = (
        "Jesteś asystentem pomagającym znaleźć odpowiedni paczkomat InPost. "
        "Otrzymasz listę punktów i pytanie użytkownika. "
        "Odpowiedz zwięźle po polsku, wskazując konkretne punkty (ID + adres), które pasują do zapytania. "
        "Jeśli żaden nie pasuje, powiedz o tym wprost."
    )
    user_prompt = (
        f"Dostępne punkty (próbka {sample_size} z {len(pool)}):\n{sample_text}\n\n"
        f"Pytanie: {query}"
    )

    console.print(f"[dim]Pytam Claude o: {query!r}…[/dim]")
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    answer = message.content[0].text

    console.print(Panel(answer, title="🤖 InPost Scout AI", border_style="magenta"))


# ─── entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cli()
