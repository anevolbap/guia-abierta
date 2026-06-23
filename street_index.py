"""Callejero -> (page, cell) references, dedup, Spanish sort.

Output street_index.json:
  { "datos_fecha": ..., "entries": [ {"name": "...", "refs": ["12-C4", ...]}, ... ] }

Spanish collation is done by hand (no reliance on a system es_ES locale being
installed): accents fold to their base letter for primary order, and ñ is its
own letter right after n.
"""
from __future__ import annotations

import json
import unicodedata

import geopandas as gpd

from config import CFG
from grid import load_grid

_ALPHABET = "abcdefghijklmnñopqrstuvwxyz0123456789"
_RANK = {ch: i for i, ch in enumerate(_ALPHABET)}


def spanish_key(s: str) -> tuple:
    out = []
    for ch in s.lower():
        if ch == "ñ":
            out.append(_RANK["ñ"])
            continue
        base = unicodedata.normalize("NFD", ch)[0]
        if base in _RANK:
            out.append(_RANK[base])
        elif ch.isspace():
            out.append(-1)  # spaces sort before letters
    return tuple(out)


def _name_col(gdf: gpd.GeoDataFrame) -> str:
    for cand in ("nombre", "NOMBRE", "nom", "nomoficial", "NOM", "name", "calle"):
        if cand in gdf.columns:
            return cand
    raise ValueError(f"no street-name column in {list(gdf.columns)}")


def _ref_sort_key(ref: str) -> tuple:
    # "12-C4" -> (12, "C", 4)
    page, cell = ref.split("-")
    return (int(page), cell[0], int(cell[1:]))


def build_street_index() -> dict:
    calles = gpd.read_file(CFG.data_dir / "calles.geojson").to_crs(CFG.crs_work)
    cells = load_grid()["cells"]
    name_col = _name_col(calles)

    calles = calles[[name_col, calles.geometry.name]].copy()
    calles = calles[calles[name_col].notna()]
    joined = gpd.sjoin(calles, cells[["ref", "geometry"]], predicate="intersects")

    by_name: dict[str, set[str]] = {}
    for name, ref in zip(joined[name_col], joined["ref"]):
        by_name.setdefault(str(name).strip(), set()).add(ref)

    entries = []
    for name in sorted(by_name, key=spanish_key):
        refs = sorted(by_name[name], key=_ref_sort_key)
        entries.append({"name": name, "refs": refs})

    result = {"datos_fecha": CFG.datos_fecha, "count": len(entries), "entries": entries}
    out = CFG.output_dir / "street_index.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[street_index] {len(entries)} streets -> {out.name}")
    return result


if __name__ == "__main__":
    build_street_index()
