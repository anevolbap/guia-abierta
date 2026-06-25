"""Core deliverable: line <-> cell cross-reference for colectivos + subte.

Two sources, one output shape:
  line_to_cells.json   per line: ordered cells (ida/vuelta if the data has it,
                       else merged), tagged by mode.
  cell_to_lines.json   per cell: the lines passing through it, tagged by mode,
                       so the booklet can say "29" or "Subte D".

Colectivo data is geometry-only AMBA recorridos (format auto-detected). Subte
is real GTFS parsed with gtfs_kit. A coverage gate guards against the wrong
feed (the ~27-line city colectivo feed instead of the ~137-line AMBA one).
"""
from __future__ import annotations

import json
import math
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely import STRtree
from shapely.geometry import MultiLineString
from shapely.ops import linemerge, unary_union

from config import CFG
from grid import load_grid
from names import abbreviate

LINE_COL_CANDIDATES = [
    "LINEA", "linea", "Linea", "LÍNEA", "linea_desc", "nombre", "NOMBRE",
    "route", "RECORRIDO", "ramal_desc", "nom", "agency_name", "n_linea",
]
DIR_COL_CANDIDATES = [
    "sentido", "SENTIDO", "Sentido", "direction", "ida_vuelta", "sent",
]
RAMAL_COL_CANDIDATES = [
    "Recorrido", "RECORRIDO", "recorrido", "ramal", "RAMAL", "Ramal", "ramal_desc",
]


# --------------------------------------------------------------------------
# cell ordering
# --------------------------------------------------------------------------
def _cells_sindex(cells: gpd.GeoDataFrame):
    return cells, cells.sindex


def _line_parts(geom) -> list:
    """Flatten any geometry to its constituent LineStrings (clip can yield a
    GeometryCollection mixing points/lines)."""
    if geom.is_empty:
        return []
    gt = geom.geom_type
    if gt == "LineString":
        return [geom]
    if gt == "MultiLineString":
        return list(geom.geoms)
    if gt == "GeometryCollection":
        out = []
        for g in geom.geoms:
            out.extend(_line_parts(g))
        return out
    return []  # points / polygons ignored


def order_cells_along(geom, cells: gpd.GeoDataFrame, sindex) -> list[str]:
    """Cells touched by a line, in traversal order (first-entry wins)."""
    lines = _line_parts(geom)
    if not lines:
        return []
    merged = linemerge(lines) if len(lines) > 1 else lines[0]
    parts = list(merged.geoms) if isinstance(merged, MultiLineString) else [merged]
    step = min(CFG.cell_w_m, CFG.cell_h_m) / 3.0
    ordered: list[str] = []
    seen: set[str] = set()
    for part in parts:
        if part.is_empty or part.length == 0:
            continue
        n = max(2, int(part.length / step) + 1)
        for k in range(n + 1):
            pt = part.interpolate(min(part.length, k * step))
            for idx in sindex.intersection((pt.x, pt.y, pt.x, pt.y)):
                ref = cells.iloc[idx]["ref"]
                if cells.iloc[idx].geometry.covers(pt):
                    if ref not in seen:
                        seen.add(ref)
                        ordered.append(ref)
                    break
    return ordered


# --------------------------------------------------------------------------
# colectivos (AMBA recorridos, geometry only)
# --------------------------------------------------------------------------
def _find_colectivos_file() -> Path:
    for ext in ("geojson", "json", "shp", "zip", "kml", "kmz", "gpkg"):
        p = CFG.data_dir / f"colectivos.{ext}"
        if p.exists():
            return p
    raise FileNotFoundError("no colectivos.* in data/ (run fetch first)")


def read_colectivos() -> gpd.GeoDataFrame:
    p = _find_colectivos_file()
    if p.suffix == ".zip":
        gdf = gpd.read_file(f"zip://{p}")
    elif p.suffix == ".kmz":
        with zipfile.ZipFile(p) as z:
            kml = next(n for n in z.namelist() if n.endswith(".kml"))
            z.extract(kml, CFG.data_dir)
        gdf = gpd.read_file(CFG.data_dir / kml)
    elif p.suffix == ".kml":
        try:
            gdf = gpd.read_file(p)
        except Exception:
            gdf = gpd.read_file(p, driver="KML")
    else:
        gdf = gpd.read_file(p)
    return gdf.to_crs(CFG.crs_work)


def _pick_col(gdf: gpd.GeoDataFrame, candidates: list[str]) -> str | None:
    lower = {c.lower(): c for c in gdf.columns}
    for cand in candidates:
        if cand in gdf.columns:
            return cand
        if cand.lower() in lower:
            return lower[cand.lower()]
    return None


def colectivo_lines(clip_geom) -> dict[str, dict[str, object]]:
    """{ line_name: {direction|'merged': geometry} } clipped to the booklet's
    rendered area (union of page tiles), so coverage matches what is drawn."""
    gdf = read_colectivos()
    gdf = gdf[gdf.intersects(clip_geom)].copy()
    gdf["geometry"] = gdf.geometry.intersection(clip_geom)
    gdf = gdf[~gdf.geometry.is_empty]

    line_col = _pick_col(gdf, LINE_COL_CANDIDATES)
    if line_col is None:
        raise RuntimeError(
            f"no line column found in colectivos; columns={list(gdf.columns)}"
        )
    dir_col = _pick_col(gdf, DIR_COL_CANDIDATES)
    ramal_col = _pick_col(gdf, RAMAL_COL_CANDIDATES)
    if ramal_col == line_col:
        ramal_col = None
    has_dir = dir_col is not None and gdf[dir_col].nunique(dropna=True) >= 2
    has_ramal = ramal_col is not None and gdf[ramal_col].nunique(dropna=True) >= 1
    print(f"[transit] colectivo line_col={line_col!r} dir_col={dir_col!r} "
          f"ramal_col={ramal_col!r} split_directions={has_dir}")

    # group by line (+ ramal) (+ direction); key encodes "ramal::dir" so each
    # ramal keeps its own route -- a wrong ramal is a wrong destination.
    group_cols = [line_col] + ([ramal_col] if has_ramal else []) + ([dir_col] if has_dir else [])
    out: dict[str, dict[str, object]] = {}
    for keys, grp in gdf.groupby(group_cols):
        vals = dict(zip(group_cols, keys if isinstance(keys, tuple) else (keys,), strict=True))
        line = str(vals[line_col]).strip()
        ramal = str(vals[ramal_col]).strip() if has_ramal else ""
        d = _norm_dir(vals[dir_col]) if has_dir else "merged"
        key = f"{ramal}::{d}" if has_ramal else d
        out.setdefault(line, {})[key] = unary_union(grp.geometry.values)
    return out


def _norm_dir(value) -> str:
    s = str(value).strip().lower()
    if s in ("ida", "i", "0", "1_ida"):
        return "ida"
    if s in ("vuelta", "v", "regreso", "1", "2_vuelta"):
        return "vuelta"
    return s or "merged"


# --------------------------------------------------------------------------
# subte (GTFS)
# --------------------------------------------------------------------------
def _read_gtfs(name: str):
    import pandas as pd

    zpath = CFG.data_dir / "subte_gtfs.zip"
    with zipfile.ZipFile(zpath) as z:
        member = next(n for n in z.namelist() if n.endswith(name))
        with z.open(member) as f:
            return pd.read_csv(f)


def subte_lines() -> dict[str, dict[str, object]]:
    """{ route_short_name: {direction|'merged': geometry} } from GTFS shapes.

    Built straight from the GTFS tables (shapes/trips/routes) to avoid
    gtfs_kit API drift across versions.
    """
    from shapely.geometry import LineString

    shapes = _read_gtfs("shapes.txt")
    trips = _read_gtfs("trips.txt")
    routes = _read_gtfs("routes.txt")
    name_col = "route_short_name" if "route_short_name" in routes.columns else "route_long_name"

    # one LineString per shape_id (ordered by sequence), in WGS84
    geom_by_shape: dict[object, object] = {}
    for shape_id, grp in shapes.sort_values("shape_pt_sequence").groupby("shape_id"):
        pts = list(zip(grp["shape_pt_lon"], grp["shape_pt_lat"], strict=True))
        if len(pts) >= 2:
            geom_by_shape[shape_id] = LineString(pts)

    shp = gpd.GeoDataFrame(
        {"shape_id": list(geom_by_shape)},
        geometry=list(geom_by_shape.values()),
        crs=CFG.crs_geo,
    ).to_crs(CFG.crs_work)
    geom_by_shape = dict(zip(shp["shape_id"], shp.geometry, strict=True))

    has_dir = "direction_id" in trips.columns and trips["direction_id"].nunique(dropna=True) >= 2
    cols = ["route_id", "shape_id"] + (["direction_id"] if has_dir else [])
    link = trips[cols].drop_duplicates().merge(routes[["route_id", name_col]], on="route_id")

    out: dict[str, dict[str, object]] = {}
    for _, r in link.iterrows():
        geom = geom_by_shape.get(r["shape_id"])
        if geom is None:
            continue
        line = str(r[name_col]).strip()
        d = "merged"
        if has_dir:
            d = "ida" if int(r["direction_id"]) == 0 else "vuelta"
        prev = out.setdefault(line, {}).get(d)
        out[line][d] = unary_union([prev, geom]) if prev is not None else geom
    return out


# --------------------------------------------------------------------------
# route -> street names (so the line index reads as a route, not coordinates)
# --------------------------------------------------------------------------
def _load_street_network():
    """calles geometries + display names + an STRtree, in the work CRS."""
    calles = gpd.read_file(CFG.data_dir / "calles.geojson").to_crs(CFG.crs_work)
    namecol = next((c for c in ("nom_mapa", "nomoficial", "nombre", "nom")
                    if c in calles.columns), None)
    geoms = list(calles.geometry.values)
    names = [abbreviate(str(v)) if (namecol and pd.notna(v := calles.iloc[i][namecol]))
             else "" for i in range(len(calles))]
    return geoms, names, STRtree(geoms)


def _seg_endpoints(geom):
    if geom.geom_type == "LineString":
        return geom.coords[0], geom.coords[-1]
    if geom.geom_type == "MultiLineString" and len(geom.geoms):
        longest = max(geom.geoms, key=lambda g: g.length)
        return longest.coords[0], longest.coords[-1]
    return None


def route_streets(route, geoms, names, tree, corridor_m=12.0, max_angle=35.0):
    """Ordered street names a route travels ALONG (crossings filtered out by a
    corridor-overlap + parallelism test). Consecutive duplicates collapsed."""
    if route is None or route.is_empty:
        return []
    route = linemerge(route) if route.geom_type != "LineString" else route
    corridor = route.buffer(corridor_m)
    try:
        idxs = tree.query(corridor, predicate="intersects")
    except Exception:
        idxs = tree.query(corridor)
    items = []
    for i in idxs:
        i = int(i)
        nm = names[i]
        if not nm:
            continue
        seg = geoms[i]
        inter = seg.intersection(corridor)
        ilen = inter.length
        if ilen < 25:
            continue
        if ilen < 0.5 * seg.length and ilen < 60:
            continue  # likely a crossing, not travelled along
        ends = _seg_endpoints(seg)
        if ends is None:
            continue
        try:
            d = route.project(seg.interpolate(0.5, normalized=True))
            a = route.interpolate(max(0.0, d - 6))
            b = route.interpolate(min(route.length, d + 6))
        except Exception:
            continue
        rb = math.degrees(math.atan2(b.y - a.y, b.x - a.x))
        sb = math.degrees(math.atan2(ends[1][1] - ends[0][1], ends[1][0] - ends[0][0]))
        diff = abs(rb - sb) % 180
        diff = min(diff, 180 - diff)
        if diff > max_angle:
            continue  # crosses the route, not parallel to it
        items.append((d, nm))
    items.sort(key=lambda t: t[0])
    out, seen = [], set()
    for _, nm in items:
        if _is_junk_street(nm) or nm in seen:
            continue
        seen.add(nm)
        out.append(nm)
    return out


_JUNK_STREET = ("TUNEL", "VIADUCTO", "PUENTE", "ACCESO", "CALZADA", "DARSENA",
                "ROTONDA", "BAJADA", "SUBIDA", "EMPALME", "CRUCE", "PEAJE")


def _is_junk_street(name: str) -> bool:
    u = name.upper()
    return any(k in u for k in _JUNK_STREET)


def _merge_route_streets(seqs):
    seqs = [s for s in seqs if s]
    if not seqs:
        return []
    return max(seqs, key=len)  # the fuller direction is a fine description


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------
def build_transit_index() -> dict:
    grid = load_grid()
    cells = grid["cells"]
    cells, sindex = _cells_sindex(cells)
    clip_geom = unary_union(grid["pages"].geometry.values)  # rendered area

    lines_out = []
    cell_to_lines: dict[str, list[dict]] = {}
    print("[transit] loading street network for route descriptions...")
    geoms, names, tree = _load_street_network()

    def add(mode: str, source: dict[str, dict[str, object]]) -> int:
        kept = 0
        for line, dirs in source.items():
            directions = {}
            routes = {}
            seqs = []
            for dname, geom in dirs.items():
                refs = order_cells_along(geom, cells, sindex)
                directions[dname] = refs
                streets = route_streets(geom, geoms, names, tree)
                routes[dname] = streets
                seqs.append(streets)
                for ref in refs:
                    tag = {"mode": mode, "line": line}
                    bucket = cell_to_lines.setdefault(ref, [])
                    if tag not in bucket:
                        bucket.append(tag)
            # drop lines that never enter the booklet (all directions empty)
            if not any(directions.values()):
                continue
            kept += 1
            lines_out.append({"mode": mode, "line": line, "directions": directions,
                              "routes": routes, "streets": _merge_route_streets(seqs)})
        return kept

    n_col = n_sub = 0
    if CFG.modes.get("colectivo", True):
        n_col = add("colectivo", colectivo_lines(clip_geom))
    if CFG.modes.get("subte", True):
        n_sub = add("subte", subte_lines())

    _coverage_gate(n_col, n_sub)

    # stable ordering
    for ref in cell_to_lines:
        cell_to_lines[ref].sort(key=lambda t: (t["mode"], _line_sort(t["line"])))
    lines_out.sort(key=lambda x: (x["mode"], _line_sort(x["line"])))

    l2c = {"datos_fecha": CFG.datos_fecha, "lines": lines_out}
    c2l = {"datos_fecha": CFG.datos_fecha,
           "cells": dict(sorted(cell_to_lines.items(), key=lambda kv: _ref_key(kv[0])))}
    (CFG.output_dir / "line_to_cells.json").write_text(
        json.dumps(l2c, ensure_ascii=False, indent=2), encoding="utf-8")
    (CFG.output_dir / "cell_to_lines.json").write_text(
        json.dumps(c2l, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[transit] colectivo lines={n_col} subte lines={n_sub} "
          f"cells with service={len(cell_to_lines)}")
    return {"line_to_cells": l2c, "cell_to_lines": c2l}


def _coverage_gate(n_col: int, n_sub: int) -> None:
    g = CFG.coverage_gate
    if CFG.mvp_enabled:
        print(f"[transit] MVP mode: coverage gate skipped "
              f"(colectivo={n_col}, subte={n_sub})")
        return
    if CFG.modes.get("colectivo", True):
        lo, hi = g.get("colectivo_min_lines", 120), g.get("colectivo_max_lines", 180)
        if not (lo <= n_col <= hi):
            raise AssertionError(
                f"colectivo coverage {n_col} outside [{lo},{hi}] -- wrong feed? "
                "The city colectivos-gtfs carries only ~27 lines; use AMBA recorridos."
            )
    if CFG.modes.get("subte", True):
        if n_sub < g.get("subte_min_lines", 6):
            raise AssertionError(f"subte coverage {n_sub} < {g.get('subte_min_lines', 6)}")


def _line_sort(line: str):
    return (0, int(line)) if str(line).isdigit() else (1, str(line))


def _ref_key(ref: str):
    page, cell = ref.split("-")
    return (int(page), cell[0], int(cell[1:]))


if __name__ == "__main__":
    build_transit_index()
