"""Download + cache every input. Idempotent: existing files are reused.

Portals are CKAN, so we resolve resource URLs through the CKAN API
(`package_show`) instead of hardcoding resource ids that rotate. A direct
URL override in config.yaml short-circuits the lookup.

Outputs in data/:
  colectivos.*        AMBA recorridos geometry (format auto-detected)
  subte_gtfs.zip      Subte GTFS
  calles.geojson      Callejero
  barrios.geojson     Barrios (also the CABA clip boundary)
  landmarks_osm.gpkg  OSM POIs (fetched lazily by landmarks.py if missing)
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import requests

from config import CFG

UA = {"User-Agent": "guiat-remake/0.1 (open data booklet; contact via repo)"}
TIMEOUT = 120


def _get(url: str, **kw) -> requests.Response:
    r = requests.get(url, headers=UA, timeout=TIMEOUT, **kw)
    r.raise_for_status()
    return r


def ckan_resources(base: str, dataset: str) -> list[dict]:
    url = f"{base}/api/3/action/package_show"
    r = _get(url, params={"id": dataset})
    data = r.json()
    if not data.get("success"):
        raise RuntimeError(f"CKAN package_show failed for {dataset}: {data}")
    return data["result"]["resources"]


def pick_resource(resources: list[dict], formats: list[str]) -> dict:
    """Pick the first resource whose format/url matches a preference order."""
    norm = lambda s: (s or "").lower().strip()
    for fmt in formats:
        for res in resources:
            if norm(res.get("format")) == fmt or norm(res.get("url")).endswith(f".{fmt}"):
                return res
    # last resort: anything with a downloadable url
    for res in resources:
        if res.get("url"):
            return res
    raise RuntimeError("no downloadable resource found")


def download(url: str, dest: Path) -> Path:
    if dest.exists() and dest.stat().st_size > 0:
        print(f"[fetch] cached {dest.name}")
        return dest
    print(f"[fetch] GET {url}")
    r = _get(url, stream=True)
    dest.write_bytes(r.content)
    print(f"[fetch] saved {dest.name} ({dest.stat().st_size//1024} KiB)")
    return dest


def fetch_colectivos() -> Path:
    """AMBA recorridos geometry. Format unknown up front: try GeoJSON, SHP
    (zip), KML in that order. Returns the cached file path; the extension
    tells transit_index how to read it."""
    s = CFG.sources
    if s.get("colectivos_url"):
        url = s["colectivos_url"]
        ext = url.rsplit(".", 1)[-1].split("?")[0].lower()
        return download(url, CFG.data_dir / f"colectivos.{ext}")

    res = pick_resource(
        ckan_resources(s["transporte_ckan"], s["colectivos_dataset"]),
        ["geojson", "json", "zip", "shp", "kml", "kmz"],
    )
    url = res["url"]
    fmt = (res.get("format") or url.rsplit(".", 1)[-1]).lower()
    ext = {"json": "geojson", "kmz": "kmz"}.get(fmt, fmt)
    return download(url, CFG.data_dir / f"colectivos.{ext}")


def fetch_subte_gtfs() -> Path:
    s = CFG.sources
    dest = CFG.data_dir / "subte_gtfs.zip"
    if dest.exists():
        print("[fetch] cached subte_gtfs.zip")
        return dest
    url = s.get("subte_gtfs_url") or pick_resource(
        ckan_resources(s["ba_ckan"], s["subte_dataset"]), ["zip"]
    )["url"]
    download(url, dest)
    _normalize_gtfs_zip(dest)
    return dest


def _normalize_gtfs_zip(dest: Path) -> None:
    """The portal wraps the GTFS in an outer zip (one nested .zip entry).
    Unwrap so dest is a real GTFS zip readable by gtfs_kit."""
    needed = {"routes.txt", "trips.txt", "stops.txt"}
    with zipfile.ZipFile(dest) as z:
        names = z.namelist()
        if needed.issubset({Path(n).name for n in names}):
            return
        # single nested zip -> unwrap it
        if len(names) == 1:
            inner = z.read(names[0])
            with zipfile.ZipFile(io.BytesIO(inner)) as z2:
                inner_names = {Path(n).name for n in z2.namelist()}
            if needed.issubset(inner_names):
                dest.write_bytes(inner)
                print(f"[fetch] unwrapped nested GTFS zip in {dest.name}")
                return
    raise RuntimeError(f"subte zip missing GTFS files; got {names[:8]}")


def fetch_geojson(dataset_key: str, override_key: str, out_name: str) -> Path:
    s = CFG.sources
    dest = CFG.data_dir / out_name
    if dest.exists():
        print(f"[fetch] cached {out_name}")
        return dest
    url = s.get(override_key) or pick_resource(
        ckan_resources(s["ba_ckan"], s[dataset_key]),
        ["geojson", "json"],
    )["url"]
    return download(url, dest)


def fetch_calles() -> Path:
    return fetch_geojson("calles_dataset", "calles_url", "calles.geojson")


def fetch_barrios() -> Path:
    return fetch_geojson("barrios_dataset", "barrios_url", "barrios.geojson")


def fetch_manzanas() -> Path:
    return fetch_geojson("manzanas_dataset", "manzanas_url", "manzanas.geojson")


def fetch_bici() -> Path:
    """Ecobici public bike stations (new system). The dataset holds several
    resources; pick_resource prefers the GeoJSON (point per station)."""
    return fetch_geojson("bici_dataset", "bici_url", "bici.geojson")


def fetch_all() -> dict[str, Path]:
    out: dict[str, Path] = {}
    out["barrios"] = fetch_barrios()
    out["calles"] = fetch_calles()
    out["manzanas"] = fetch_manzanas()
    if CFG.modes.get("colectivo", True):
        out["colectivos"] = fetch_colectivos()
    if CFG.modes.get("subte", True):
        out["subte"] = fetch_subte_gtfs()
    if CFG.modes.get("bici", True):
        out["bici"] = fetch_bici()
    # OSM landmarks are fetched lazily by landmarks.py (needs the clip polygon).
    return out


if __name__ == "__main__":
    for k, v in fetch_all().items():
        print(f"  {k:12s} -> {v}")
