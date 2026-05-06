"""
Generates an interactive HTML map using folium + MarkerCluster.
The output is a single self-contained .html file — no server needed.
"""

from __future__ import annotations
from pathlib import Path

from .models import Point

# Colour per point type — makes the map instantly readable
TYPE_COLOURS = {
    "parcel_locker": "#E85D04",   # orange — the iconic InPost colour
    "pok":           "#2D6A4F",   # dark green — points of service
    "pop":           "#1D3557",   # dark blue — pick-up points
}
DEFAULT_COLOUR = "#6B7280"  # grey for anything else


def _colour_for(point: Point) -> str:
    return TYPE_COLOURS.get(point.type.lower(), DEFAULT_COLOUR)


def _popup_html(point: Point) -> str:
    """Build a small HTML card shown when a marker is clicked."""
    badge_colour = _colour_for(point)
    h24 = "✅ 24/7" if point.is_next_24h else "🕐 Godziny ograniczone"
    status_colour = "#16a34a" if point.is_operating else "#dc2626"
    functions_html = ""
    if point.functions:
        tags = "".join(
            f'<span style="background:#f3f4f6;border-radius:4px;padding:2px 6px;font-size:11px;margin:2px;display:inline-block">{f}</span>'
            for f in point.functions
        )
        functions_html = f'<div style="margin-top:6px">{tags}</div>'

    return f"""
    <div style="font-family:system-ui,sans-serif;min-width:200px;max-width:260px">
      <div style="background:{badge_colour};color:#fff;padding:6px 10px;border-radius:6px 6px 0 0;font-weight:700;font-size:13px">
        {point.name}
      </div>
      <div style="padding:8px 10px;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 6px 6px">
        <div style="font-size:12px;color:#374151">{point.address.line1}</div>
        <div style="font-size:12px;color:#6b7280;margin-bottom:4px">{point.address.line2}</div>
        <div style="font-size:12px">
          <span style="color:{status_colour};font-weight:600">{point.status}</span>
          &nbsp;·&nbsp;{h24}
        </div>
        {functions_html}
        {"<div style='font-size:11px;color:#9ca3af;margin-top:4px'>" + point.operating_hours + "</div>" if point.operating_hours else ""}
      </div>
    </div>
    """.strip()


def generate_map(
    points: list[Point],
    output_path: Path = Path("inpost_map.html"),
    title: str = "InPost Scout — Mapa paczekomatów",
) -> Path:
    """
    Build a clustered interactive map and save it to output_path.

    Returns the output path so callers can report where the file was saved.
    """
    try:
        import folium
        from folium.plugins import MarkerCluster
    except ImportError:
        raise ImportError(
            "folium is required for map generation. Install it with: pip install folium"
        )

    if not points:
        raise ValueError("No points to display on the map.")

    # Centre the map on Poland
    centre_lat = sum(p.location.latitude for p in points) / len(points)
    centre_lon = sum(p.location.longitude for p in points) / len(points)

    m = folium.Map(
        location=[centre_lat, centre_lon],
        zoom_start=7,
        tiles="CartoDB positron",
    )

    # Title overlay
    title_html = f"""
    <div style="position:fixed;top:12px;left:50%;transform:translateX(-50%);
                background:#fff;padding:8px 18px;border-radius:8px;
                box-shadow:0 2px 8px rgba(0,0,0,.15);font-family:system-ui;
                font-size:14px;font-weight:700;color:#111;z-index:9999">
      {title} &nbsp;<span style="font-weight:400;color:#6b7280">({len(points):,} punktów)</span>
    </div>
    """
    m.get_root().html.add_child(folium.Element(title_html))

    # Legend
    legend_items = "".join(
        f'<div style="display:flex;align-items:center;gap:6px;margin:3px 0">'
        f'<span style="width:12px;height:12px;background:{colour};border-radius:50%;display:inline-block"></span>'
        f'<span style="font-size:12px">{label}</span></div>'
        for label, colour in [
            ("Paczkomat", TYPE_COLOURS["parcel_locker"]),
            ("Punkt obsługi (POK)", TYPE_COLOURS["pok"]),
            ("Punkt odbioru (POP)", TYPE_COLOURS["pop"]),
            ("Inny", DEFAULT_COLOUR),
        ]
    )
    legend_html = f"""
    <div style="position:fixed;bottom:24px;right:12px;background:#fff;
                padding:10px 14px;border-radius:8px;
                box-shadow:0 2px 8px rgba(0,0,0,.15);font-family:system-ui;z-index:9999">
      <div style="font-weight:700;font-size:12px;margin-bottom:6px;color:#111">Typ punktu</div>
      {legend_items}
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    cluster = MarkerCluster(
        options={
            "maxClusterRadius": 40,
            "disableClusteringAtZoom": 14,
        }
    ).add_to(m)

    for point in points:
        colour = _colour_for(point)
        folium.CircleMarker(
            location=[point.location.latitude, point.location.longitude],
            radius=6,
            color=colour,
            fill=True,
            fill_color=colour,
            fill_opacity=0.85,
            weight=1.5,
            popup=folium.Popup(_popup_html(point), max_width=280),
            tooltip=f"{point.name} — {point.address.city}",
        ).add_to(cluster)

    m.save(str(output_path))
    return output_path
