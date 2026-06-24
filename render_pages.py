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
from mpl_style import GUIA, SUBTE, SUBTE_DARK_TEXT, apply_rcparams
from names import abbreviate

apply_rcparams()

SUBTE_COLORS = SUBTE
# parks drawn as area fills; everything else is a labelled marker
FILL_STYLE = {
    "parque": {"color": GUIA["park_face"], "edgecolor": GUIA["park_edge"]},
}
FILL_CATS = set(FILL_STYLE)


def _street_label_col(gdf):
    for c in ("nom_mapa", "nomoficial", "nombre", "nom"):
        if c in gdf.columns:
            return c
    return None


def _load_layers():
    manz = None
    manz_path = CFG.data_dir / "manzanas.geojson"
    if manz_path.exists():
        manz = gpd.read_file(manz_path).to_crs(CFG.crs_work)
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
    return manz, streets, osm, subte_geo, stations


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
    ax.set_facecolor(GUIA["map_base"])
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_linewidth(GUIA["frame_lw"])
        s.set_edgecolor(GUIA["frame"])
        s.set_zorder(GUIA["z"]["frame"])
    return ax


def _draw_fishnet(ax, tile_bounds):
    """Sub-grid lines inside the map (data coords) so they sit at z=fishnet,
    under the subte line and labels but over the blocks."""
    x0, y0, x1, y1 = tile_bounds
    for c in range(1, CFG.cols):
        x = x0 + (x1 - x0) * c / CFG.cols
        ax.plot([x, x], [y0, y1], color=GUIA["fishnet"], lw=GUIA["fishnet_lw"],
                zorder=GUIA["z"]["fishnet"])
    for r in range(1, CFG.rows):
        y = y1 - (y1 - y0) * r / CFG.rows
        ax.plot([x0, x1], [y, y], color=GUIA["fishnet"], lw=GUIA["fishnet_lw"],
                zorder=GUIA["z"]["fishnet"])


def _draw_gutter_labels(fig):
    """A-E / 1-7 labels in the page margins (figure coords)."""
    L = CFG.margin_left_mm / CFG.page_w_mm
    B = CFG.margin_bottom_mm / CFG.page_h_mm
    W = CFG.map_w_mm / CFG.page_w_mm
    H = CFG.map_h_mm / CFG.page_h_mm
    over = fig.add_axes([0, 0, 1, 1])
    over.set_axis_off()
    over.set_xlim(0, 1)
    over.set_ylim(0, 1)
    for c in range(CFG.cols):
        x = L + W * (c + 0.5) / CFG.cols
        over.text(x, B + H + 0.006, CFG.col_labels[c], ha="center", va="bottom",
                  fontsize=GUIA["fs_gutter"], weight="bold", color=GUIA["muted"])
    for r in range(CFG.rows):
        y = B + H * (1 - (r + 0.5) / CFG.rows)
        over.text(L - 0.006, y, CFG.row_labels[r], ha="right", va="center",
                  fontsize=GUIA["fs_gutter"], weight="bold", color=GUIA["muted"])
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


_HALO = [pe.withStroke(linewidth=0.9, foreground=GUIA["paper"])]


def _label_streets(ax, st, bounds):
    """Place street labels with greedy collision avoidance so they stay
    readable: avenidas first, then the longest streets. A label is skipped if
    it would overlap one already placed or spill outside the map box, instead
    of cramming every name and overlapping them."""
    x0, y0, x1, y1 = bounds
    sd = CFG.scale_denom / 1000.0  # paper mm -> world metres

    cands = []
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
        fs = GUIA["fs_avenida"] if is_av else GUIA["fs_street"]
        half_w = 0.5 * len(str(name)) * 0.55 * fs * 0.3528 * sd
        half_h = 0.5 * 1.2 * fs * 0.3528 * sd
        cands.append((is_av, part.length, str(name), mid, ang, fs, half_w, half_h))

    cands.sort(key=lambda c: (0 if c[0] else 1, -c[1]))  # avenidas, then longest
    placed = []  # axis-aligned (x, y, rx, ry) of the rotated label box
    for is_av, _seglen, name, mid, ang, fs, hw, hh in cands:
        c, s = abs(math.cos(math.radians(ang))), abs(math.sin(math.radians(ang)))
        rx = hw * c + hh * s
        ry = hw * s + hh * c
        if mid.x - rx < x0 or mid.x + rx > x1 or mid.y - ry < y0 or mid.y + ry > y1:
            continue  # would spill outside the box
        if any(abs(mid.x - px) < (rx + prx) * 0.78 and abs(mid.y - py) < (ry + pry) * 0.78
               for px, py, prx, pry in placed):
            continue  # would overlap a placed label
        placed.append((mid.x, mid.y, rx, ry))
        ax.text(mid.x, mid.y, name, rotation=ang, rotation_mode="anchor",
                ha="center", va="center", clip_on=True, zorder=GUIA["z"]["labels"],
                fontsize=fs, weight="bold",
                color=GUIA["avenida_label"] if is_av else GUIA["street_label"],
                path_effects=_HALO)


def render_page(page_no, tile, layers):
    manz, streets, osm, subte_geo, stations = layers
    x0, y0, x1, y1 = tile.bounds
    bounds = (x0, y0, x1, y1)
    clip = gpd.GeoDataFrame(geometry=[tile], crs=CFG.crs_work)

    fig = plt.figure(figsize=(CFG.mm_to_in(CFG.page_w_mm), CFG.mm_to_in(CFG.page_h_mm)))
    fig.patch.set_facecolor(GUIA["paper"])
    ax = _axes_for_page(fig, bounds)
    Z = GUIA["z"]

    # city blocks (manzanas): filled so streets read as the base-coloured gaps
    if manz is not None:
        blocks = manz.cx[x0:x1, y0:y1]
        if not blocks.empty:
            blocks.plot(ax=ax, facecolor=GUIA["manzana_fill"], edgecolor="none",
                        zorder=Z["manzanas"])

    # avenidas as a casing (edge colour under, fill colour on top)
    st = gpd.clip(streets.cx[x0:x1, y0:y1], clip)
    avs = st[st["__av"]]
    if not avs.empty:
        avs.plot(ax=ax, color=GUIA["avenida_edge"], lw=GUIA["avenida_casing_lw"],
                 zorder=Z["avenidas"], capstyle="round")
        avs.plot(ax=ax, color=GUIA["avenida_fill"], lw=GUIA["avenida_lw"],
                 zorder=Z["avenidas"] + 0.1, capstyle="round")

    # parks as translucent green fills
    if osm is not None:
        for cat, style in FILL_STYLE.items():
            area = gpd.clip(osm[osm["category"] == cat], clip)
            if not area.empty:
                area.plot(ax=ax, lw=0.4, zorder=Z["park"], **style)

    _draw_fishnet(ax, bounds)

    # subte lines, each in its line colour
    for line, geom in subte_geo.items():
        g = gpd.clip(gpd.GeoDataFrame(geometry=[geom], crs=CFG.crs_work), clip)
        if g.empty:
            continue
        g.plot(ax=ax, color=SUBTE_COLORS.get(str(line).upper(), GUIA["subte_line_lw"] and "#00925A"),
               lw=GUIA["subte_line_lw"] + 0.6, zorder=Z["subte"], capstyle="round")

    # subte stations: white face + thin ink ring
    if stations is not None:
        ss = gpd.clip(stations, clip)
        for _, s in ss.iterrows():
            ax.plot(s.geometry.x, s.geometry.y, "o", ms=GUIA["station_size"],
                    mfc=GUIA["station_face"], mec=GUIA["station_ring"],
                    mew=GUIA["station_ring_lw"], zorder=Z["stations"])
            ax.annotate(str(s["name"]), (s.geometry.x, s.geometry.y),
                        xytext=(2, 2), textcoords="offset points",
                        fontsize=GUIA["fs_station"], color=GUIA["park_label"],
                        zorder=Z["labels"], path_effects=_HALO)

    if not st.empty:
        _label_streets(ax, st, bounds)

    # point landmarks (hospitals + other major), one marker per name per page
    if osm is not None:
        pts = osm[~osm["category"].isin(FILL_CATS)]
        pts = gpd.clip(pts, clip).drop_duplicates(subset="name")
        for _, p in pts.iterrows():
            rp = p.geometry.representative_point()
            ax.plot(rp.x, rp.y, "s", ms=2.4, color=GUIA["accent"], zorder=Z["stations"])
            ax.annotate(str(p["name"]), (rp.x, rp.y), xytext=(2, 2),
                        textcoords="offset points", fontsize=GUIA["fs_station"],
                        color=GUIA["ink"], zorder=Z["labels"], path_effects=_HALO)

    _draw_gutter_labels(fig)

    # folio (page number) in the header band, Archivo Black, accent
    fig.text(0.5, 1 - CFG.margin_top_mm / CFG.page_h_mm / 2, str(page_no),
             ha="center", va="center", fontsize=GUIA["fs_folio"],
             fontfamily="Archivo Black", color=GUIA["accent"])

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
    fig.patch.set_facecolor(GUIA["paper"])
    left = CFG.margin_left_mm / CFG.page_w_mm
    bottom = CFG.margin_bottom_mm / CFG.page_h_mm
    width = CFG.map_w_mm / CFG.page_w_mm
    height = CFG.map_h_mm / CFG.page_h_mm
    ax = fig.add_axes([left, bottom, width, height])
    ax.set_xlim(0, CFG.cols)
    ax.set_ylim(0, CFG.rows)
    ax.set_facecolor(GUIA["paper"])
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():           # outer frame
        s.set_linewidth(GUIA["frame_lw"])
        s.set_edgecolor(GUIA["frame"])
    for c in range(1, CFG.cols):           # inner separators
        ax.plot([c, c], [0, CFG.rows], color=GUIA["cell_sep"], lw=GUIA["cell_sep_lw"])
    for r in range(1, CFG.rows):
        ax.plot([0, CFG.cols], [r, r], color=GUIA["cell_sep"], lw=GUIA["cell_sep_lw"])
    for c in range(CFG.cols):
        ax.text(c + 0.5, CFG.rows + 0.08, CFG.col_labels[c], ha="center",
                va="bottom", fontsize=GUIA["fs_gutter"], weight="bold",
                color=GUIA["muted"], clip_on=False)
    for r in range(CFG.rows):
        ax.text(-0.08, CFG.rows - r - 0.5, CFG.row_labels[r], ha="right",
                va="center", fontsize=GUIA["fs_gutter"], weight="bold",
                color=GUIA["muted"], clip_on=False)

    for _, cell in page_cells.iterrows():
        col, row, ref = int(cell["col"]), int(cell["row"]), cell["ref"]
        tags = lines_by_ref.get(ref, [])
        col_nums = sorted((t["line"] for t in tags if t["mode"] == "colectivo"),
                          key=_line_key)
        subte = sorted((t["line"] for t in tags if t["mode"] == "subte"),
                       key=_line_key)
        cx = col + 0.5
        if subte:
            # rounded-square badges in the bottom-right of the cell
            step = 0.24
            by = CFG.rows - row - 0.85
            bx0 = col + 0.96 - step * len(subte)
            for i, letter in enumerate(subte):
                u = str(letter).upper()
                fc = SUBTE_COLORS.get(u, "#00925A")
                tc = GUIA["ink"] if u in SUBTE_DARK_TEXT else "#FFFFFF"
                ax.text(bx0 + i * step + step / 2, by, str(letter), fontsize=5.0,
                        ha="center", va="center", color=tc, clip_on=True,
                        fontfamily="Archivo Black",
                        bbox=dict(boxstyle="round,pad=0.16,rounding_size=0.25",
                                  ec="none", fc=fc))
        if col_nums:
            n = len(col_nums)
            joined = ", ".join(_fmt_colectivo(l) for l in col_nums)
            # wrap into a near-square block, then size the font from the ACTUAL
            # wrapped geometry. Top-anchored under any subte badge with a
            # conservative height budget so even dense cells never spill over.
            w_items = max(1, round(math.sqrt(n * 0.8)))
            wrap = max(6, round(w_items * len(joined) / n))
            txt = textwrap.fill(joined, width=wrap)
            lines = txt.split("\n")
            n_lines, max_len = len(lines), max(len(s) for s in lines)
            avail = 18.5 if subte else 22.5   # subte leaves bottom room for badge
            fs_h = avail / (n_lines * 1.3) / 0.3528
            fs_w = 24.0 / (max_len * 0.55) / 0.3528
            # narrow band so cells look harmonised (sparse cells don't balloon)
            fs = max(4.8, min(7.6, fs_h, fs_w))
            top = CFG.rows - row - 0.11
            ax.text(cx, top, txt, ha="center", va="top", fontsize=fs,
                    color=GUIA["cell_text"], linespacing=1.12, clip_on=True)

    # folio, Archivo Black accent, in the header band (matches the map page)
    fig.text(0.5, 1 - CFG.margin_top_mm / CFG.page_h_mm / 2, str(page_no),
             ha="center", va="center", fontsize=GUIA["fs_folio"],
             fontfamily="Archivo Black", color=GUIA["accent"])
    out = CFG.pages_dir / f"{page_no:02d}_lines.pdf"
    fig.savefig(out)
    plt.close(fig)
    return out


def render_all():
    # clear stale page PDFs so a shorter run does not leave old pages behind
    for old in CFG.pages_dir.glob("*.pdf"):
        old.unlink()
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
