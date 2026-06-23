"""Render one vector A5 PDF per page at the configured true scale.

Each page draws: streets + sub-grid (A-E / 1-7) + landmarks + subte
lines/stations. NO colectivo overlays (that is what the cell<->line index is
for; ~137 route lines would be spaghetti). Scale is exact because the axes box
is physically map_w_mm x map_h_mm and spans page_w_m x page_h_m of data.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import geopandas as gpd
import matplotlib.pyplot as plt

from config import CFG
from grid import load_grid

SUBTE_COLORS = {
    "A": "#38b6ff", "B": "#e30613", "C": "#005aab", "D": "#009b3a",
    "E": "#6d2c91", "H": "#ffd200", "P": "#00a651", "PM": "#00a651",
}
PARK_CATS = {"plaza", "parque"}


def _load_layers():
    streets = gpd.read_file(CFG.data_dir / "calles.geojson").to_crs(CFG.crs_work)
    osm = None
    osm_path = CFG.data_dir / "landmarks_osm.gpkg"
    if osm_path.exists():
        osm = gpd.read_file(osm_path).to_crs(CFG.crs_work)
    subte_geo = {}
    stations = None
    if CFG.modes.get("subte", True):
        from transit_index import subte_lines
        from landmarks import subte_stations

        for line, dirs in subte_lines().items():
            from shapely.ops import unary_union

            subte_geo[line] = unary_union(list(dirs.values()))
        stations = subte_stations().to_crs(CFG.crs_work)
    return streets, osm, subte_geo, stations


def _axes_for_page(fig, tile_bounds):
    x0, y0, x1, y1 = tile_bounds
    left = CFG.margin_left_mm / CFG.page_w_mm
    bottom = CFG.margin_bottom_mm / CFG.page_h_mm
    width = CFG.map_w_mm / CFG.page_w_mm
    height = CFG.map_h_mm / CFG.page_h_mm
    ax = fig.add_axes([left, bottom, width, height])
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_linewidth(0.8)
    return ax


def _draw_subgrid(fig):
    """Sub-grid overlay in figure coords so labels sit in the margins."""
    L = CFG.margin_left_mm / CFG.page_w_mm
    B = CFG.margin_bottom_mm / CFG.page_h_mm
    W = CFG.map_w_mm / CFG.page_w_mm
    H = CFG.map_h_mm / CFG.page_h_mm
    over = fig.add_axes([0, 0, 1, 1])
    over.set_axis_off()
    over.set_xlim(0, 1)
    over.set_ylim(0, 1)
    for c in range(1, CFG.cols):
        x = L + W * c / CFG.cols
        over.plot([x, x], [B, B + H], color="0.55", lw=0.4, ls=(0, (4, 3)))
    for r in range(1, CFG.rows):
        y = B + H * (1 - r / CFG.rows)
        over.plot([L, L + W], [y, y], color="0.55", lw=0.4, ls=(0, (4, 3)))
    for c in range(CFG.cols):
        x = L + W * (c + 0.5) / CFG.cols
        over.text(x, B + H + 0.006, CFG.col_labels[c], ha="center", va="bottom",
                  fontsize=7, weight="bold")
    for r in range(CFG.rows):
        y = B + H * (1 - (r + 0.5) / CFG.rows)
        over.text(L - 0.006, y, CFG.row_labels[r], ha="right", va="center",
                  fontsize=7, weight="bold")
    return over


def render_page(page_no, tile, layers):
    streets, osm, subte_geo, stations = layers
    bounds = tile.bounds
    clip = gpd.GeoDataFrame(geometry=[tile], crs=CFG.crs_work)

    fig = plt.figure(figsize=(CFG.mm_to_in(CFG.page_w_mm), CFG.mm_to_in(CFG.page_h_mm)))
    ax = _axes_for_page(fig, bounds)

    # parks/plazas as light fill (context)
    if osm is not None:
        parks = osm[osm["category"].isin(PARK_CATS)]
        parks = gpd.clip(parks, clip)
        if not parks.empty:
            parks.plot(ax=ax, color="#d7ecd2", edgecolor="#b6d8ad", lw=0.3, zorder=1)

    # streets
    st = gpd.clip(streets, clip)
    if not st.empty:
        st.plot(ax=ax, color="0.35", lw=0.35, zorder=2)

    # subte lines
    for line, geom in subte_geo.items():
        g = gpd.clip(gpd.GeoDataFrame(geometry=[geom], crs=CFG.crs_work), clip)
        if g.empty:
            continue
        g.plot(ax=ax, color=SUBTE_COLORS.get(str(line).upper(), "#444"),
               lw=2.2, zorder=3, capstyle="round")

    # subte stations
    if stations is not None:
        ss = gpd.clip(stations, clip)
        for _, s in ss.iterrows():
            ax.plot(s.geometry.x, s.geometry.y, "o", ms=3.2, mfc="white",
                    mec="black", mew=0.7, zorder=4)
            ax.annotate(str(s["name"]), (s.geometry.x, s.geometry.y),
                        xytext=(2, 2), textcoords="offset points",
                        fontsize=4.2, zorder=5)

    # point landmarks with labels (hospitals, estadios, civico, cementerios)
    if osm is not None:
        pts = osm[~osm["category"].isin(PARK_CATS)]
        pts = gpd.clip(pts, clip)
        for _, p in pts.iterrows():
            rp = p.geometry.representative_point()
            ax.plot(rp.x, rp.y, "s", ms=2.4, color="#c0392b", zorder=4)
            ax.annotate(str(p["name"]), (rp.x, rp.y), xytext=(2, 2),
                        textcoords="offset points", fontsize=4.2, color="#7b241c",
                        zorder=5)

    _draw_subgrid(fig)

    # header + footer in figure coords
    fig.text(0.5, 1 - CFG.margin_top_mm / CFG.page_h_mm / 2, str(page_no),
             ha="center", va="center", fontsize=11, weight="bold")
    fig.text(0.5, CFG.margin_bottom_mm / CFG.page_h_mm / 2,
             f"Guía T · 1:{int(CFG.scale_denom)} · datos {CFG.datos_fecha} · "
             "OSM (ODbL) + AMBA (CC-BY)", ha="center", va="center", fontsize=4)

    out = CFG.pages_dir / f"{page_no:02d}.pdf"
    fig.savefig(out)
    plt.close(fig)
    return out


def render_all():
    pages = load_grid()["pages"]
    layers = _load_layers()
    outs = []
    for _, prow in pages.iterrows():
        page_no = int(prow["page"])
        outs.append(render_page(page_no, prow.geometry, layers))
    print(f"[render] {len(outs)} pages -> {CFG.pages_dir}")
    return outs


if __name__ == "__main__":
    render_all()
