"""OSM POIs + subte stations -> classified landmarks assigned to (page, cell).

Output landmarks.json:
  { "entries": [ {"name","category","ref","mode"}, ... ] }
landmarks.json feeds both the maps (render_pages) and the landmark index
(frontmatter). The OSM pull is cached to data/landmarks_osm.gpkg.
"""
from __future__ import annotations

import json
import zipfile

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from config import CFG
from grid import load_boundary, load_grid


def _osm_tags() -> dict:
    """Flatten config categories into a single osmnx tags dict."""
    tags: dict[str, set] = {}
    for sels in CFG.landmark_categories.values():
        for key, val in sels:
            tags.setdefault(key, set()).add(val)
    return {k: sorted(v) for k, v in tags.items()}


def _classify(row) -> str | None:
    for cat, sels in CFG.landmark_categories.items():
        for key, val in sels:
            if str(row.get(key, "")) == val:
                return cat
    return None


def fetch_osm_landmarks() -> gpd.GeoDataFrame:
    cache = CFG.data_dir / "landmarks_osm.gpkg"
    if cache.exists():
        return gpd.read_file(cache)
    import osmnx as ox

    poly = load_boundary().to_crs(CFG.crs_geo).iloc[0]
    if not poly.is_valid:
        poly = poly.buffer(0)  # reprojection can reintroduce self-intersections
    feats = ox.features_from_polygon(poly, _osm_tags())
    feats = feats.reset_index()
    # keep only named features; classify
    feats["category"] = feats.apply(_classify, axis=1)
    feats = feats[feats["category"].notna()].copy()
    if "name" not in feats.columns:
        feats["name"] = None
    feats = feats[feats["name"].notna()].copy()
    feats = feats[["name", "category", "geometry"]]
    feats = _drop_small(feats)
    feats.to_file(cache, driver="GPKG")
    print(f"[landmarks] OSM features cached: {len(feats)} -> {cache.name}")
    return feats


def _drop_small(feats: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Keep large_only categories (parks/cemeteries) only above the area
    threshold; everything else passes regardless of size."""
    if feats.empty or not CFG.landmark_large_only:
        return feats
    area_m2 = feats.to_crs(CFG.crs_work).geometry.area
    big = feats["category"].isin(CFG.landmark_large_only)
    drop = big & (area_m2.values < CFG.min_major_area_m2)
    return feats[~drop].copy()


def subte_stations() -> gpd.GeoDataFrame:
    if not CFG.modes.get("subte", True):
        return gpd.GeoDataFrame(columns=["name", "category", "geometry"], crs=CFG.crs_geo)
    zpath = CFG.data_dir / "subte_gtfs.zip"
    with zipfile.ZipFile(zpath) as z:
        name = next(n for n in z.namelist() if n.endswith("stops.txt"))
        with z.open(name) as f:
            stops = pd.read_csv(f)
    # parent stations only when present, else all stops
    if "location_type" in stops.columns and (stops["location_type"] == 1).any():
        stops = stops[stops["location_type"] == 1]
    geom = [Point(xy) for xy in zip(stops["stop_lon"], stops["stop_lat"], strict=True)]
    gdf = gpd.GeoDataFrame(
        {"name": stops["stop_name"].astype(str), "category": "estacion_subte"},
        geometry=geom,
        crs=CFG.crs_geo,
    )
    return gdf


def bici_stations() -> gpd.GeoDataFrame:
    """Ecobici stations from the cached point GeoJSON. Kept separate from the
    landmark index: they are drawn as bare markers on the map, not labelled."""
    if not CFG.modes.get("bici", True):
        return gpd.GeoDataFrame(columns=["name", "category", "geometry"], crs=CFG.crs_geo)
    path = CFG.data_dir / "bici.geojson"
    gdf = gpd.read_file(path).to_crs(CFG.crs_geo)
    name = gdf["NOMBRE"].astype(str) if "NOMBRE" in gdf.columns else ""
    return gpd.GeoDataFrame(
        {"name": name, "category": "estacion_bici"},
        geometry=gdf.geometry,
        crs=CFG.crs_geo,
    )


def build_landmarks() -> dict:
    parts = []
    try:
        parts.append(fetch_osm_landmarks().to_crs(CFG.crs_work))
    except Exception as e:  # OSM/Overpass can be flaky; degrade gracefully
        print(f"[landmarks] WARNING OSM fetch failed: {e}")
    parts.append(subte_stations().to_crs(CFG.crs_work))
    lm = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs=CFG.crs_work)

    # representative point for polygon features
    lm["geometry"] = lm.geometry.representative_point()

    cells = load_grid()["cells"]
    joined = gpd.sjoin(lm, cells[["page", "ref", "geometry"]], predicate="within")

    entries = []
    seen = set()
    for _, r in joined.iterrows():
        key = (str(r["name"]).strip(), r["ref"])
        if key in seen:
            continue
        seen.add(key)
        mode = "subte" if r["category"] == "estacion_subte" else "poi"
        entries.append(
            {"name": str(r["name"]).strip(), "category": r["category"],
             "ref": r["ref"], "page": int(r["page"]), "mode": mode}
        )

    entries.sort(key=lambda e: (e["page"], e["ref"], e["name"]))
    result = {"datos_fecha": CFG.datos_fecha, "count": len(entries), "entries": entries}
    out = CFG.output_dir / "landmarks.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[landmarks] {len(entries)} landmarks -> {out.name}")
    return result


if __name__ == "__main__":
    build_landmarks()
