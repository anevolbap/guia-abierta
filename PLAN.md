# Guía T Remake — Build Spec

Open-source, printable **A5 PDF booklet** for navigating Buenos Aires by colectivo/train, in the style of the Guía T. Generated from open data. Offline-final (no QR codes, no live lookups — the booklet is self-sufficient).

## Stack
- **Python** for all geoprocessing and both indices: `geopandas`, `shapely`, `pyproj`.
- **GTFS parsing**: `gtfs_kit` (or `partridge`).
- **Map rendering (MVP)**: `geopandas`/`matplotlib` → vector PDF per page. Fully scriptable, no GUI.
- **Front/back matter**: `weasyprint` (HTML/CSS → PDF) for cover + indices.
- **Assembly**: `pypdf` to merge into one A5 booklet.
- *Phase 2 upgrade*: swap map rendering to QGIS Atlas (PyQGIS) for collision-aware labels.

## Data sources (download + cache locally)
- **Colectivos (PRIMARY — full coverage)**: Ministerio de Transporte, *Recorridos de servicios de colectivos AMBA* — `https://datos.transporte.gob.ar/dataset/recorridos-de-servicios-de-colectivos-amba` (CC-BY 4.0). Covers all ~137 lines through CABA. Clip to the CABA boundary. **Do NOT use the city `colectivos-gtfs` feed as primary** — it carries only the ~27 city-jurisdiction lines.
  - **Format: geometry-only ("recorrido por línea"), NOT GTFS.** Read as vector (KML/SHP/GeoJSON) with geopandas. First-run check: confirm whether ida/vuelta are separate features or merged — drives the line index.
  - Caveat: last refreshed ~2022–23; routes drift. Acceptable — datasets can be re-fetched later; print a "datos a fecha X" line.
- **Subte (clean GTFS — has lines, stations, directions)**: `https://data.buenosaires.gob.ar/dataset/subte-gtfs`. 6 lines (A–E, H) + Premetro. Use real `gtfs_kit` parsing here.
- **Landmarks (INCLUDED)**: OSM POIs via `osmnx`/Overpass — plazas, parques, hospitales, estaciones (tren/subte), estadios, cementerios, edificios cívicos. Plus subte stations from the GTFS above.
- Trenes GTFS (phase 2 rail): `https://data.buenosaires.gob.ar/dataset/trenes-gtfs`.
- Callejero (streets): `https://data.buenosaires.gob.ar/dataset/calles` (GeoJSON).
- Barrios: `https://data.buenosaires.gob.ar/dataset/barrios` (overview map + CABA clip boundary).
- OSM (water, parks, rail) via `osmnx` for visual context.

## Baked-in decisions
- **CRS**: reproject everything to **EPSG:9498** (POSGAR 2007 Faja 5) so pages share a uniform real-world scale.
- **Page tile**: A5 (148×210 mm), portrait. Map area ~138×190 mm.
- **Scale**: start at **1:20000** (→ ~2.76×3.8 km per page → ~36–40 pages for CABA, close to the original). Scale is the main tuning knob; expose in config.
- **Sub-grid**: 5 cols (A–E) × 7 rows (1–7) per page → cell refs like `12-C4`.
- **Page numbering**: reading order (left→right, top→bottom) over the tile grid.
- **Directions**: split **ida/vuelta** only if the colectivo geometry provides it; otherwise treat each línea as one merged recorrido (acceptable — cross-reference works either way). Subte directions come cleanly from its GTFS.
- **Maps draw streets + sub-grid + landmarks + subte lines/stations. NO colectivo route lines** (avoids ~137-line spaghetti). Subte is exempt: only 6 color-coded lines, iconic, low clutter — and the original shows them.
- **Clip the page grid to the CABA boundary** (barrios union) and **drop empty pages** (no streets) so no pages are wasted on the río or empty land.

## Pipeline (each = one module)
1. **config.py** — bbox, CRS, scale, A5 dims, sub-grid size, modes (colectivo/subte), landmark categories, paths. Single source of truth.
2. **fetch.py** — download colectivo geometry + subte GTFS + callejero + barrios + OSM landmarks; cache to `data/`.
3. **grid.py** — rectangular page fishnet over the CABA-clipped bbox in EPSG:9498; assign page numbers; generate sub-grid cells per page. → `grid.gpkg` (pages + cells layers).
4. **street_index.py** — spatial-join callejero → (page, cell); dedup; locale-aware Spanish sort (ñ/accents). → `street_index.json`.
5. **landmarks.py** — pull + classify OSM POIs (+ subte stations); assign each to (page, cell). → `landmarks.json`. Feeds both the maps and a landmark index.
6. **transit_index.py** (core deliverable) — two sources, one output shape:
   - Colectivos: read the AMBA geometry (vector), clip to CABA, per línea intersect with sub-grid cells.
   - Subte: parse GTFS, per line build shape, intersect cells.
   - Emit `line_to_cells.json` (per línea: ordered cells; ida/vuelta if available, else merged) and `cell_to_lines.json` (per celda: líneas, **tagged by mode** so cross-reference can say "29" or "Subte D").
   - **Coverage gate**: assert ~130–140 distinct colectivo lines + 6 subte intersect CABA; else fail loudly (wrong feed). Start from Battocchia's logic (github.com/matiasbattocchia/bondis).
7. **render_pages.py** — per page: clip streets + landmarks + subte lines/stations to tile; draw sub-grid + labels; export `pages/NN.pdf`. **No colectivo overlays.**
8. **frontmatter.py** — cover, barrios overview (with page-grid ref), street index, line index, landmark index → PDFs via WeasyPrint.
9. **assemble.py** — merge cover → indices → pages into `output/guiat.pdf`.

Orchestrate with a `main.py` or `Makefile` running 1→8.

## MVP (the weekend target)
- Scope to **one barrio**, ~4 pages, 2–3 colectivo lines, any subte line crossing it, a handful of landmarks (stations + plazas).
- Prove the full round-trip: pick two plazas, confirm the booklet's cross-reference (`cell_to_lines`) returns the correct bus or subte.
- Output a real, printable 4-page A5 PDF.

## Phase 2
- Full CABA, then conurbano (messier multi-jurisdiction data).
- Trains (Trenes GTFS) as a third mode.
- Full landmark categories + a useful-info section (the original's back matter).
- QGIS Atlas for better label placement.
- Booklet imposition (signatures) for physical printing.

## Repo layout
```
guiat/
  config.py  fetch.py  grid.py
  street_index.py  landmarks.py
  transit_index.py
  render_pages.py  frontmatter.py  assemble.py
  main.py
data/        # cached downloads
output/      # guiat.pdf, intermediates
config.yaml
```

## Notes for the implementer
- Validate CRS reprojection early (a warped grid is the classic failure).
- GTFS shapes can be messy; dedup/merge shape variants per (route, direction).
- Keep the booklet **offline-final**: no scan-to-view, indices must be comprehensive enough to trust.
- License: data is CC-BY 4.0 (AMBA recorridos) + ODbL (OSM) — attribute both. No AGPL obligation (OCitySMap is *not* a dependency); your own code can be any license (MIT fine).
