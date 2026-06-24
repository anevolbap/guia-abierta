"""Render one vector A5 PDF per page at the configured true scale.

Each page draws: streets + sub-grid (A-E / 1-7) + landmarks + subte
lines/stations. NO colectivo overlays (that is what the cell<->line index is
for; ~137 route lines would be spaghetti). Scale is exact because the axes box
is physically map_w_mm x map_h_mm and spans page_w_m x page_h_m of data.
"""
from __future__ import annotations

import json
import math
import textwrap

import matplotlib

matplotlib.use("Agg")
import geopandas as gpd
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt

from config import CFG
from grid import load_grid
from names import abbreviate

SUBTE_COLORS = {
    "A": "#38b6ff", "B": "#e30613", "C": "#005aab", "D": "#009b3a",
    "E": "#6d2c91", "H": "#ffd200", "P": "#00a651", "PM": "#00a651",
}
# drawn as area fills; everything else is a labelled marker
FILL_STYLE = {
    "parque": {"color": "#d7ecd2", "edgecolor": "#b6d8ad"},
}
FILL_CATS = set(FILL_STYLE)


def _street_label_col(gdf):
    for c in ("nom_mapa", "nomoficial", "nombre", "nom"):
        if c in gdf.columns:
            return c
    return None


def _load_layers():
    streets = gpd.read_file(CFG.data_dir / "calles.geojson").to_crs(CFG.crs_work)
    lab = _street_label_col(streets)
    streets["__label"] = (streets[lab].fillna("").map(abbreviate) if lab else "")
    streets["__av"] = (streets["tipo_c"].astype(str).str.upper().str.contains("AVENIDA")
                       if "tipo_c" in streets.columns else False)
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


def _longest_line(geom):
    """Longest LineString component of any geometry, or None."""
    if geom is None or geom.is_empty:
        return None
    gt = geom.geom_type
    if gt == "LineString":
        return geom
    parts = []
    if gt in ("MultiLineString", "GeometryCollection"):
        for g in geom.geoms:
            p = _longest_line(g)
            if p is not None:
                parts.append(p)
    return max(parts, key=lambda p: p.length) if parts else None


_HALO = [pe.withStroke(linewidth=0.9, foreground="white")]


def _label_streets(ax, st):
    """Label EVERY street on the page (one bold, halo'd label per name, placed
    along its longest on-page run). The white halo lifts the name off the
    street lines; usability requires every street to be named."""
    for name, grp in st.groupby("__label"):
        if not name:
            continue
        part = _longest_line(grp.geometry.unary_union)
        if part is None or part.length == 0:
            continue
        is_av = bool(grp["__av"].any())
        mid = part.interpolate(0.5, normalized=True)
        p1 = part.interpolate(0.45, normalized=True)
        p2 = part.interpolate(0.55, normalized=True)
        ang = math.degrees(math.atan2(p2.y - p1.y, p2.x - p1.x))
        if ang > 90:
            ang -= 180
        elif ang < -90:
            ang += 180
        ax.text(mid.x, mid.y, str(name), rotation=ang, rotation_mode="anchor",
                ha="center", va="center", clip_on=True, zorder=2.6,
                fontsize=4.8 if is_av else 3.7, weight="bold",
                color="#13386e" if is_av else "#111", path_effects=_HALO)


def render_page(page_no, tile, layers):
    streets, osm, subte_geo, stations = layers
    bounds = tile.bounds
    clip = gpd.GeoDataFrame(geometry=[tile], crs=CFG.crs_work)

    fig = plt.figure(figsize=(CFG.mm_to_in(CFG.page_w_mm), CFG.mm_to_in(CFG.page_h_mm)))
    ax = _axes_for_page(fig, bounds)

    # parks / cemeteries as light area fills (context)
    if osm is not None:
        for cat, style in FILL_STYLE.items():
            area = gpd.clip(osm[osm["category"] == cat], clip)
            if not area.empty:
                area.plot(ax=ax, lw=0.3, zorder=1, **style)

    # streets + names
    st = gpd.clip(streets, clip)
    if not st.empty:
        st.plot(ax=ax, color="0.35", lw=0.35, zorder=2)
        _label_streets(ax, st)

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

    # point landmarks with labels (hospitals + other major). One marker per
    # name per page so repeated OSM features (e.g. campuses) do not clutter.
    if osm is not None:
        pts = osm[~osm["category"].isin(FILL_CATS)]
        pts = gpd.clip(pts, clip).drop_duplicates(subset="name")
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


def _line_key(line):
    return (0, int(line)) if str(line).isdigit() else (1, str(line))


def _fmt_colectivo(line):
    s = str(line)
    return str(int(s)) if s.isdigit() else s


def render_transit_page(page_no, page_cells, lines_by_ref):
    """The Guía T facing page: same A-E / 1-7 grid as the map, but each cell
    lists the lines passing through it. Read your cell on the map, flip here,
    read the buses. Colectivos as numbers, subte as a coloured letter."""
    fig = plt.figure(figsize=(CFG.mm_to_in(CFG.page_w_mm), CFG.mm_to_in(CFG.page_h_mm)))
    left = CFG.margin_left_mm / CFG.page_w_mm
    bottom = CFG.margin_bottom_mm / CFG.page_h_mm
    width = CFG.map_w_mm / CFG.page_w_mm
    height = CFG.map_h_mm / CFG.page_h_mm
    ax = fig.add_axes([left, bottom, width, height])
    ax.set_xlim(0, CFG.cols)
    ax.set_ylim(0, CFG.rows)
    ax.set_xticks([])
    ax.set_yticks([])
    for c in range(CFG.cols + 1):
        ax.plot([c, c], [0, CFG.rows], color="0.55", lw=0.5)
    for r in range(CFG.rows + 1):
        ax.plot([0, CFG.cols], [r, r], color="0.55", lw=0.5)
    for c in range(CFG.cols):
        ax.text(c + 0.5, CFG.rows + 0.1, CFG.col_labels[c], ha="center",
                va="bottom", fontsize=7, weight="bold", clip_on=False)
    for r in range(CFG.rows):
        ax.text(-0.1, CFG.rows - r - 0.5, CFG.row_labels[r], ha="right",
                va="center", fontsize=7, weight="bold", clip_on=False)

    for _, cell in page_cells.iterrows():
        col, row, ref = int(cell["col"]), int(cell["row"]), cell["ref"]
        tags = lines_by_ref.get(ref, [])
        col_nums = sorted((t["line"] for t in tags if t["mode"] == "colectivo"),
                          key=_line_key)
        subte = sorted((t["line"] for t in tags if t["mode"] == "subte"),
                       key=_line_key)
        cx = col + 0.5
        if subte:
            step = 0.2
            x0 = cx - (len(subte) - 1) * step / 2
            y = CFG.rows - row - 0.22
            for i, letter in enumerate(subte):
                ax.text(x0 + i * step, y, str(letter), fontsize=3.6, ha="center",
                        va="center", color="white", clip_on=True,
                        bbox=dict(boxstyle="square,pad=0.15", ec="none",
                                  fc=SUBTE_COLORS.get(str(letter).upper(), "#444")))
        if col_nums:
            fs = 3.4 if len(col_nums) <= 10 else (2.9 if len(col_nums) <= 16 else 2.5)
            txt = textwrap.fill(" ".join(_fmt_colectivo(l) for l in col_nums), width=12)
            yc = CFG.rows - row - 0.5 - (0.14 if subte else 0.0)
            ax.text(cx, yc, txt, ha="center", va="center", fontsize=fs,
                    color="#111", linespacing=0.9, clip_on=True)

    fig.text(0.5, 1 - CFG.margin_top_mm / CFG.page_h_mm / 2, f"{page_no} · líneas",
             ha="center", va="center", fontsize=10, weight="bold")
    fig.text(0.5, CFG.margin_bottom_mm / CFG.page_h_mm / 2,
             f"Líneas por celda (misma grilla que el mapa pág. {page_no}). "
             "Número = colectivo · letra de color = subte.",
             ha="center", va="center", fontsize=4)
    out = CFG.pages_dir / f"{page_no:02d}_lines.pdf"
    fig.savefig(out)
    plt.close(fig)
    return out


def render_all():
    grid = load_grid()
    pages, cells = grid["pages"], grid["cells"]
    layers = _load_layers()
    c2l_path = CFG.output_dir / "cell_to_lines.json"
    lines_by_ref = {}
    if c2l_path.exists():
        lines_by_ref = json.loads(c2l_path.read_text(encoding="utf-8"))["cells"]
    else:
        print("[render] WARNING cell_to_lines.json missing; skipping line pages")

    outs = []
    for _, prow in pages.iterrows():
        page_no = int(prow["page"])
        outs.append(render_page(page_no, prow.geometry, layers))
        if lines_by_ref:
            page_cells = cells[cells["page"] == page_no]
            outs.append(render_transit_page(page_no, page_cells, lines_by_ref))
    print(f"[render] {len(outs)} page PDFs (map + líneas) -> {CFG.pages_dir}")
    return outs


if __name__ == "__main__":
    render_all()
