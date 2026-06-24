# Guía T Remake — design and decisions

Reference doc for the build. Records what was built, what the data actually
looked like, and every decision made while implementing `PLAN.md`. Read this
before changing the pipeline.

## Status

Full pipeline runs end to end and produces a real printable A5 PDF. Verified
both in MVP mode (barrio Palermo) and in full-CABA mode.

Full CABA run (`mvp.enabled: false`):
- 29 map pages, 1015 sub-grid cells. Empty río tiles dropped.
- Maps draw street names (avenidas emphasised, names abbreviated) and major
  landmarks. Denser labelling than the first pass.
- 4733 street index entries (2972 split by house-number range).
- 704 landmarks (hospitals + major: parks, stations, universities, civic).
- 138 colectivo lines + 8 subte (A-E, H, 2 premetro); 842 cells with service.
  The coverage gate ([120,180] colectivo, >=6 subte) passes.
- Every map page is followed by its line-grid page (the Guía T facing page).
- Final `output/guiat.pdf`: 178 pages, A5 confirmed. Round-trip verified:
  "CORRIENTES AV. 0-1000" -> cell 9-E4 -> buses 19/39/42/... + Subte B.

MVP run (`mvp.enabled: true`, Palermo) for comparison: 4 map pages, 658 street
entries, 62 landmarks, 24-page booklet.

Round-trip check (the MVP acceptance test) passes: a landmark resolves to a
cell, and the cell resolves back to the right lines. Examples:
- Subte station "Jose Hernandez" -> cell `1-A7` -> `subte D` + 14 colectivos.
- Subte station "Dorrego" -> cell `3-A5` -> `subte B`.

## What the data actually is

These were the open questions in `PLAN.md`. Answers from the live downloads:

- Colectivos (AMBA recorridos) is a single **KML**, one layer
  `Lineas_JN_RMBA_CNRT2`, 1128 LineString features. Useful columns:
  `Linea` (138 distinct lines, zero-padded like `001`), `Recorrido` (ramal:
  A, B, ...), `Sentido` (`IDA` / `VUELTA`). So **ida/vuelta is provided** and we
  split on it. Ramales of the same line are merged per direction.
- The KML driver is not enabled in Fiona's whitelist, but GeoPandas reads it
  through the **pyogrio** engine (the default), so no special handling is
  needed beyond `gpd.read_file`.
- Subte GTFS downloads as a zip that **wraps another zip** (a single entry named
  `subte_gtfs` that is itself the real GTFS). `fetch.py` unwraps it. The GTFS
  has `shapes.txt`, `trips.txt` with `direction_id`, and `route_short_name`
  values A, B, C, D, E, H plus two Premetro routes (`PM-C`, `PM-S`).
- Barrios and Callejero both offer a GeoJSON resource on the CKAN portal; we
  pick those. Barrio name column is `nombre`. Street name column is `nombre`.

## Baked-in decisions (from the spec, confirmed)

- CRS `EPSG:9498` (POSGAR 2007 Faja 5). Validated as metric at startup. At
  1:20000 a page tile is 2760 x 3800 m and a cell is 552 x 543 m.
- A5 portrait, map window 138 x 190 mm inside configurable margins.
- Sub-grid 5 cols (A-E) x 7 rows (1-7); refs like `12-C4`.
- Page numbering in reading order: top row first, left to right.
- Maps draw streets + sub-grid + landmarks + subte lines/stations. **No
  colectivo route lines** (137 lines would be spaghetti). Subte is drawn (6
  color-coded lines).
- Offline-final: no QR codes, no live lookups. The indices carry everything.

## Decisions I made while implementing

1. **MVP barrio = Palermo, not Chacarita.** Chacarita is small enough to fit in
   a single page at 1:20000, which does not exercise multi-page numbering or
   cross-page indices. Palermo spans a 2x2 page grid, has the Subte D line and
   several stations, and large parks. Better proof of the round-trip. Change
   `mvp.barrio` in `config.yaml` to scope elsewhere.

2. **Clip transit to the union of page tiles, not the barrio polygon.** The
   rendered pages are rectangles that extend past the barrio outline, and the
   maps draw streets in that whole rectangle. So the index must reflect the
   rectangle, not the barrio. Clipping colectivos to the barrio polygon (as the
   spec's "clip to CABA" implies) would have made colectivo coverage
   inconsistent with subte coverage and with what is actually drawn. In a full
   CABA run the page tiles already approximate CABA, so this is equivalent
   there and strictly more correct in MVP.

3. **Lines that never enter the booklet are dropped** from the line index.
   `subte_lines()` returns all subte routes; only those with at least one cell
   in the booklet are listed. Avoids empty entries like "Subte A: (none)".

4. **Cell ordering by first entry along the line.** `order_cells_along` merges
   the line, walks it at 1/3-cell steps, and records each cell the first time
   the path enters it. Gives a human-sensible ordered cell list per line/
   direction without needing stop sequences (the colectivo data has none).

5. **Spanish collation by hand**, not via a system locale. Accents fold to the
   base letter for primary order and ñ is its own letter right after n. Avoids
   depending on `es_ES.UTF-8` being installed. See `street_index.spanish_key`.

6. **Coverage gate is skipped in MVP** (a single barrio legitimately has far
   fewer than 120 lines) and enforced only in full mode, where it guards
   against accidentally using the ~27-line city GTFS instead of the ~137-line
   AMBA feed.

7. **gtfs_kit is not used for geometry.** Its `geometrize_shapes` API differs
   across versions and broke. Subte shapes are built straight from
   `shapes.txt` / `trips.txt` / `routes.txt` with pandas + shapely. More robust.
   `gtfs_kit` stays a declared dependency for possible Phase 2 use.

8. **Exact print scale via axes geometry.** Each page is an A5 figure; the map
   axes box is positioned to be physically `map_w_mm x map_h_mm` and its data
   limits are set to `page_w_m x page_h_m`. Because both ratios are equal, an
   equal-aspect axes fills the box exactly and the scale is a true 1:20000. This
   is the classic failure point called out in the spec, so it is handled
   explicitly rather than left to autoscaling.

9. **Landmark and OSM fetch degrade gracefully.** If Overpass is unreachable,
   `build_landmarks` warns and continues with just subte stations, so a run
   still completes.

## Map labels and index detail (added after first pass)

10. **Street names on the maps.** Each street gets one rotated label per page,
    placed at the midpoint of its longest on-page run, angled to the street.
    Avenidas (`tipo_c == AVENIDA`) are always labelled, in blue bold; other
    streets are labelled only when their on-page run is longer than
    `_MIN_LABEL_LEN_M` (170 m) to keep clutter down. Near-duplicate placements
    within 60 m are skipped. Label text uses `nom_mapa` (e.g. "AV. SANTA FE").
    This is deliberately simple (no global collision solver); QGIS Atlas in
    Phase 2 is the real fix.

11. **Landmarks reduced to hospitals + major.** Categories are now hospital,
    parque, estadio, cementerio, estacion (train), universidad, civico. Small
    plazas and gardens are dropped. Parks and cemeteries are kept only above
    `min_major_area_m2` (40000 m^2) so we get Bosques de Palermo, not every
    named square. Hospitals and other point landmarks pass regardless of size.
    On the map, one marker per name per page (repeated OSM features like
    university campuses do not stack). Parks/cemeteries draw as area fills.

12. **Street index split by house-number range.** The callejero is per-block
    with `alt_izqini/izqfin/derini/derfin` house-number fields. Each segment is
    bucketed by its lowest real number into `number_bucket_step` (1000) bins. A
    street spanning more than one bucket gets one entry per bucket
    ("CORDOBA AV. 1000-2000", "CORDOBA AV. 2000-3000", ...); a street inside one
    bucket, or with no numbering (highways), stays a single rangeless entry.
    Watch-out fixed during build: unnumbered segments yield a pandas `NaN`, and
    `NaN is None` is false, so `_bucket` must treat NaN as unnumbered or every
    segment becomes its own `(nan, nan)` bucket and the index explodes.

## Full CABA + labelling (added in second pass)

13. **Name abbreviation (`names.py`).** Common Spanish title/rank words are
    compressed (AVENIDA -> AV., GENERAL -> GRAL., DOCTOR -> DR., INGENIERO ->
    ING., PASAJE -> PJE., and so on) to save space on both the maps and in the
    index. Matching ignores accents; words already abbreviated in the source
    are left alone. Applied to map labels (`nom_mapa`) and to index names
    (`nomoficial`), so the index still sorts by surname (the source uses the
    "PAZ, GRAL. AV." surname-first form).

14. **Denser street labels.** The minimum on-page run to label a non-avenida
    street dropped from 170 m to 85 m, and the de-dup gap from 60 m to 38 m, so
    more streets are named per page. Abbreviation offsets the extra ink.

15. **Boundary geometry healed twice.** The union of all barrios is a valid
    polygon in the work CRS but reprojecting it to WGS84 reintroduces a
    self-intersection, which osmnx rejects. `grid.load_boundary` runs
    `buffer(0)` in the work CRS, and `landmarks.fetch_osm_landmarks` runs
    `buffer(0)` again on the reprojected polygon before the Overpass call. This
    only bites in full-CABA mode (a single barrio reprojects clean).

## Guía T workflow: facing line-grid page (third pass)

16. **Each map page is followed by a line-grid page.** This is the core of how
    the Guía T is used: street index -> cell ref (`12-C4`) -> map page 12 ->
    facing page "12 · líneas" -> read cell C4 -> see the buses. `render_pages`
    now emits `NN_lines.pdf` next to `NN.pdf`: the same A-E / 1-7 grid as the
    map, each cell filled from `cell_to_lines.json` with colectivo numbers
    (leading zeros stripped: `001` -> `1`) and subte as a coloured letter badge.
    Assembly interleaves them for free: `sorted()` puts `01.pdf` before
    `01_lines.pdf` before `02.pdf` because `.` (0x2E) sorts before `_` (0x5F).
    A "Cómo usar" page on the cover spells out the three steps, and the back
    line index still does the reverse lookup (line -> cells).

    Limitation: cells on major-avenue corners carry 20-30 lines and get cramped
    even at the smallest font. The original Guía T has the same dense cells.
    Lowering `scale.denominator` (smaller cells, more pages) is the relief
    valve.

17. **All streets are labelled, bold, with a white halo.** The previous
    length/proximity filters dropped some street names; usability needs every
    street named. `_label_streets` now labels every distinct name on the page
    (one label at its longest on-page run), bold, with a white `path_effects`
    halo so the name reads against the street lines. Avenidas are larger and
    blue. Cemeteries and civic buildings were dropped from the landmark set.

## Guía T visual style: block fill (fourth pass)

18. **Maps fill city blocks, streets are the white gaps.** This is the single
    most recognisable Guía T trait. Added the GCBA *manzanas catastrales*
    dataset (7.7 MB GeoJSON). The renderer fills blocks tan (`#e9e3d6`, thin
    edge) and no longer draws minor streets as lines: the white gaps between
    blocks are the streets. Avenidas are highlighted as pale-yellow corridors
    (`#f4dd7a`) sitting in their gap. Parks fill green over the blocks; subte
    lines, stations, landmarks, the sub-grid and the bold halo'd street names
    draw on top. Manzanas are subset per page with `.cx[bbox]` (fast) and the
    axes clips; only the avenida/label subset is exact-clipped. Before this the
    maps drew grey street lines on white, which did not read as a Guía T.

## Module map

| Module | Role | Key output |
|--------|------|-----------|
| `config.py` | load `config.yaml`, derive page geometry, validate CRS | `CFG` |
| `fetch.py` | CKAN resource resolution + cache; unwrap nested GTFS | `data/*` |
| `grid.py` | boundary union, page fishnet, sub-grid, reading order | `data/grid.gpkg` |
| `street_index.py` | calles -> cells, dedup, Spanish sort | `output/street_index.json` |
| `landmarks.py` | OSM POIs + subte stations -> cells | `output/landmarks.json` |
| `transit_index.py` | colectivo + subte -> line<->cell cross-reference | `output/{line_to_cells,cell_to_lines}.json` |
| `render_pages.py` | per-page vector map at true scale | `output/pages/NN.pdf` |
| `frontmatter.py` | cover + overview + 3 indices via WeasyPrint | `output/*.pdf` |
| `assemble.py` | merge into one booklet | `output/guiat.pdf` |
| `main.py` | orchestrate, with `--only` / `--from` | - |

## Output data shapes

`cell_to_lines.json` (the booklet's brain):
```json
{ "cells": { "1-A7": [ {"mode":"subte","line":"D"},
                        {"mode":"colectivo","line":"041"}, ... ] } }
```

`line_to_cells.json`:
```json
{ "lines": [ {"mode":"subte","line":"D",
              "directions": {"ida":["4-E7","4-D7",...], "vuelta":[...]}} ] }
```

## Known limitations

- Label placement is naive (matplotlib `annotate` with a fixed offset); labels
  can overlap on dense pages. Phase 2 swaps in QGIS Atlas for collision-aware
  labels, as the spec notes.
- Colectivo line numbers keep their zero padding (`001`). Sorting treats them
  as integers, but display is the raw string. Cosmetic.
- The colectivo feed was last refreshed ~2022-23; routes drift. The footer and
  cover print "datos a fecha" so the reader knows. Re-fetch later by deleting
  `data/` and rerunning.
- `min_land_fraction` drops empty tiles by land area when no street layer is
  passed to `build_grid`; passing streets gives a sharper test but the default
  orchestration uses the area test, which is enough for CABA.

## Going to full CABA

Set `mvp.enabled: false` in `config.yaml` and rerun. Expect ~36-40 pages at
1:20000 and the coverage gate to enforce 120-180 colectivo lines + >=6 subte.
Scale is the main knob: lower `scale.denominator` for more, smaller pages.

## Licenses

- AMBA recorridos: CC-BY 4.0 (Ministerio de Transporte).
- Subte / Callejero / Barrios: GCBA open data.
- Landmarks: © OpenStreetMap contributors, ODbL.

Attribution is printed on every map page and the cover. Code is MIT. No AGPL
obligation: OCitySMap is not a dependency.
