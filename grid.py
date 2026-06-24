"""Page fishnet + sub-grid in the work CRS.

Produces grid.gpkg with two layers:
  pages  one row per kept page tile (page number, geometry, land fraction)
  cells  one row per sub-grid cell (page, col, row, ref, geometry)

A tile is kept only if it has enough land (intersection with the CABA
boundary, or with streets when passed in) so we don't waste pages on the río.
Page numbers follow reading order: top->bottom rows, left->right within a row.
"""
from __future__ import annotations

import math
from functools import lru_cache

import geopandas as gpd
from shapely.geometry import box
from shapely.ops import unary_union

from config import CFG


@lru_cache(maxsize=1)
def load_boundary() -> gpd.GeoSeries:
    """CABA clip boundary in the work CRS. MVP mode narrows it to one barrio.

    Returns a single-geometry GeoSeries (the union). Cached so every module
    that needs the clip polygon shares one load.
    """
    path = CFG.data_dir / "barrios.geojson"
    gdf = gpd.read_file(path).to_crs(CFG.crs_work)
    if CFG.mvp_enabled:
        name_col = _barrio_name_col(gdf)
        sel = gdf[gdf[name_col].str.upper().str.strip() == CFG.mvp_barrio.upper()]
        if sel.empty:
            raise ValueError(
                f"MVP barrio {CFG.mvp_barrio!r} not found in {name_col}; "
                f"available: {sorted(gdf[name_col].unique())[:8]}..."
            )
        gdf = sel
    union = unary_union(gdf.geometry.values)
    if not union.is_valid:
        union = union.buffer(0)  # heal self-intersections from the barrio union
    return gpd.GeoSeries([union], crs=CFG.crs_work)


def _barrio_name_col(gdf: gpd.GeoDataFrame) -> str:
    for cand in ("BARRIO", "barrio", "nombre", "NOMBRE", "name"):
        if cand in gdf.columns:
            return cand
    # fall back to first string column
    for c in gdf.columns:
        if gdf[c].dtype == object and c != gdf.geometry.name:
            return c
    raise ValueError("no barrio name column found")


def _snap_down(value: float, step: float) -> float:
    return math.floor(value / step) * step


def build_grid(streets: gpd.GeoDataFrame | None = None) -> dict[str, gpd.GeoDataFrame]:
    boundary = load_boundary()
    bgeom = boundary.iloc[0]
    minx, miny, maxx, maxy = bgeom.bounds

    ox = _snap_down(minx, CFG.snap_origin_m)
    oy = _snap_down(miny, CFG.snap_origin_m)
    pw, ph = CFG.page_w_m, CFG.page_h_m
    nx = math.ceil((maxx - ox) / pw)
    ny = math.ceil((maxy - oy) / ph)

    # Emptiness test. Street density is the sharpest signal: a tile that is
    # mostly río or a big park carries little street length and is dropped, so
    # we don't waste pages on near-empty grids. Falls back to land area when no
    # street layer is available.
    streets_work = None
    if streets is not None and not streets.empty:
        streets_work = streets.to_crs(CFG.crs_work)
    else:
        calles = CFG.data_dir / "calles.geojson"
        if calles.exists():
            streets_work = gpd.read_file(calles).to_crs(CFG.crs_work)
    sidx = streets_work.sindex if streets_work is not None else None

    tiles = []
    dropped_empty = 0
    for j in range(ny):          # j from bottom
        for i in range(nx):      # i from left
            x0 = ox + i * pw
            y0 = oy + j * ph
            tile = box(x0, y0, x0 + pw, y0 + ph)
            inter = tile.intersection(bgeom)
            if inter.is_empty:
                continue
            land_frac = inter.area / tile.area
            if sidx is not None:
                cand = list(sidx.intersection(tile.bounds))
                slen = streets_work.iloc[cand].intersection(tile).length.sum() if cand else 0.0
                if slen < CFG.min_street_len_m:
                    dropped_empty += 1
                    continue
            elif land_frac < CFG.min_land_fraction:
                continue
            tiles.append({"i": i, "j": j, "geometry": tile, "land_fraction": land_frac})

    if not tiles:
        raise RuntimeError("no page tiles survived filtering; check scale/boundary")
    if dropped_empty:
        print(f"[grid] dropped {dropped_empty} near-empty tiles "
              f"(< {CFG.min_street_len_m:.0f} m of streets)")

    # Reading order: top row first (max j), left to right (min i).
    tiles.sort(key=lambda t: (-t["j"], t["i"]))
    if CFG.mvp_enabled:
        tiles = tiles[: CFG.mvp_max_pages]

    pages_rows = []
    cells_rows = []
    for page_no, t in enumerate(tiles, start=1):
        x0, y0, _x1, y1 = t["geometry"].bounds
        pages_rows.append(
            {
                "page": page_no,
                "i": t["i"],
                "j": t["j"],
                "land_fraction": round(t["land_fraction"], 4),
                "geometry": t["geometry"],
            }
        )
        cw, ch = CFG.cell_w_m, CFG.cell_h_m
        for col in range(CFG.cols):
            for row in range(CFG.rows):
                cx0 = x0 + col * cw
                # row 0 is the TOP of the page -> highest y
                cy1 = y1 - row * ch
                cy0 = cy1 - ch
                cell = box(cx0, cy0, cx0 + cw, cy1)
                cells_rows.append(
                    {
                        "page": page_no,
                        "col": col,
                        "row": row,
                        "ref": CFG.cell_ref(page_no, col, row),
                        "geometry": cell,
                    }
                )

    pages = gpd.GeoDataFrame(pages_rows, crs=CFG.crs_work)
    cells = gpd.GeoDataFrame(cells_rows, crs=CFG.crs_work)

    out = CFG.data_dir / "grid.gpkg"
    pages.to_file(out, layer="pages", driver="GPKG")
    cells.to_file(out, layer="cells", driver="GPKG")
    print(f"[grid] {len(pages)} pages, {len(cells)} cells -> {out.name}")
    return {"pages": pages, "cells": cells}


@lru_cache(maxsize=1)
def load_grid() -> dict[str, gpd.GeoDataFrame]:
    out = CFG.data_dir / "grid.gpkg"
    if not out.exists():
        return build_grid()
    pages = gpd.read_file(out, layer="pages")
    cells = gpd.read_file(out, layer="cells")
    return {"pages": pages, "cells": cells}


if __name__ == "__main__":
    build_grid()
