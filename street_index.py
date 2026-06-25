"""Callejero -> (page, cell) references, split by house-number range.

Output street_index.json:
  { "datos_fecha": ...,
    "entries": [ {"name": "...", "range": "1000-2000"|null, "refs": ["12-C4", ...]}, ...] }

A street that spans more than one number bucket gets one entry per bucket
(like the original Guía T). Streets confined to a single bucket, or with no
house numbering (highways), stay a single entry with range=null.

Spanish collation is done by hand (no reliance on a system es_ES locale):
accents fold to their base letter for primary order, and ñ is its own letter
right after n.
"""
from __future__ import annotations

import json
import unicodedata

import geopandas as gpd

from config import CFG
from grid import load_grid
from names import abbreviate

_ALPHABET = "abcdefghijklmnñopqrstuvwxyz0123456789"
_RANK = {ch: i for i, ch in enumerate(_ALPHABET)}
_ALT_COLS = ["alt_izqini", "alt_izqfin", "alt_derini", "alt_derfin"]


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
    for cand in ("nomoficial", "nombre", "NOMBRE", "nom", "name", "calle"):
        if cand in gdf.columns:
            return cand
    raise ValueError(f"no street-name column in {list(gdf.columns)}")


def _ref_sort_key(ref: str) -> tuple:
    page, cell = ref.split("-")
    return (int(page), cell[0], int(cell[1:]))


def _segment_low(row) -> int | None:
    """Lowest real house number on a segment, or None if unnumbered."""
    vals = []
    for c in _ALT_COLS:
        v = row.get(c)
        if v is not None and not _isnan(v) and int(v) > 0:
            vals.append(int(v))
    return min(vals) if vals else None


def _isnan(v) -> bool:
    return isinstance(v, float) and v != v


def _bucket(low) -> tuple[int, int] | None:
    if low is None or _isnan(low):
        return None
    step = CFG.number_bucket_step
    lo = (int(low) // step) * step
    return (lo, lo + step)


def build_street_index() -> dict:
    calles = gpd.read_file(CFG.data_dir / "calles.geojson").to_crs(CFG.crs_work)
    cells = load_grid()["cells"]
    name_col = _name_col(calles)

    have_alt = [c for c in _ALT_COLS if c in calles.columns]
    keep = [name_col, *have_alt, calles.geometry.name]
    calles = calles[keep].copy()
    calles = calles[calles[name_col].notna()]

    # drop unnamed streets, and (by default) cemetery internal streets
    nom_u = calles[name_col].astype(str).str.upper()
    drop = nom_u.str.contains("SIN NOMBRE OFICIAL", na=False)
    if CFG.raw.get("street_index", {}).get("hide_cemetery_streets", True):
        drop |= nom_u.str.contains("CEMENTERIO", na=False)
    calles = calles[~drop]
    calles["__low"] = calles.apply(_segment_low, axis=1) if have_alt else None

    joined = gpd.sjoin(calles, cells[["ref", "geometry"]], predicate="intersects")

    # name -> {bucket(tuple|None): set(refs)}
    by_name: dict[str, dict] = {}
    for _, r in joined.iterrows():
        name = abbreviate(str(r[name_col]).strip())
        bucket = _bucket(r["__low"]) if have_alt else None
        by_name.setdefault(name, {}).setdefault(bucket, set()).add(r["ref"])

    entries = []
    for name in by_name:
        buckets = by_name[name]
        numbered = {b: refs for b, refs in buckets.items() if b is not None}
        none_refs = buckets.get(None, set())
        if len(numbered) <= 1:
            # single entry: merge everything, no range shown
            refs = set().union(*buckets.values())
            entries.append({"name": name, "range": None, "lo": -1,
                            "refs": sorted(refs, key=_ref_sort_key)})
        else:
            first = min(numbered)
            for b in sorted(numbered):
                refs = set(numbered[b])
                if b == first:
                    refs |= none_refs  # fold unnumbered bits into the first range
                lo, hi = b
                entries.append({"name": name, "range": f"{lo}-{hi}", "lo": lo,
                                "refs": sorted(refs, key=_ref_sort_key)})

    entries.sort(key=lambda e: (spanish_key(e["name"]), e["lo"]))
    for e in entries:
        e.pop("lo")

    result = {"datos_fecha": CFG.datos_fecha, "count": len(entries), "entries": entries}
    out = CFG.output_dir / "street_index.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    n_split = sum(1 for e in entries if e["range"])
    print(f"[street_index] {len(entries)} entries ({n_split} with ranges) -> {out.name}")
    return result


if __name__ == "__main__":
    build_street_index()
