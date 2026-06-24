# Guía Abierta

[Versión en español](README.md) · English

Open-source, printable **A5 PDF booklet** for getting around Buenos Aires by
colectivo (bus) and subte (metro), in the style of the classic Guía T. Built
from open data, offline-final: no QR codes, no live lookups, the booklet is
self-sufficient. ("Guía T" is a commercial name; this project uses an original
name, see `DATA.md`.)

It is A5 portrait (148 × 210 mm), made to print as a small pocket booklet.

## How it works (the Guía T method)

1. Find your street in the **street index**, get a reference like `12-C4`
   (page 12, cell C4).
2. Go to **map page 12** and find cell C4 (letters A–E across, numbers 1–7
   down).
3. Flip to the **facing page** (the line grid): same grid, and cell C4 lists
   the lines passing through it. Numbers are buses, a coloured letter is the
   subte.

Every map page is followed by its line-grid page. Map pages deliberately do
**not** draw bus routes (≈137 lines would be spaghetti); the facing grid carries
that. Subte is drawn on the map (6 colour-coded lines). City blocks are filled
tan so streets read as the white gaps.

## Install

```bash
uv venv --python 3.11
uv pip install -e .
```

WeasyPrint needs system libraries (Pango, Cairo, GDK-PixBuf, HarfBuzz). On
Debian/Ubuntu:

```bash
sudo apt install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
                 libffi-dev libcairo2 libharfbuzz0b
```

GeoPandas/Fiona/pyproj ship binary wheels, so GDAL needs no separate install.

## Run

```bash
uv run python main.py            # full pipeline -> output/guiat.pdf
uv run python main.py --list     # list the 9 stages
uv run python main.py --only grid
uv run python main.py --from transit   # a stage and everything after
```

`config.yaml` is the single source of truth (scale, sub-grid, title, scope,
data sources). `mvp.enabled: true` scopes to one barrio for a quick test;
`false` builds all of CABA (≈26 pages).

## Pipeline

| Stage | Module | Output |
|-------|--------|--------|
| 1 | `config.py` | validated CRS + page geometry |
| 2 | `fetch.py` | cached downloads in `data/` |
| 3 | `grid.py` | `data/grid.gpkg` (pages + cells) |
| 4 | `street_index.py` | `output/street_index.json` |
| 5 | `landmarks.py` | `output/landmarks.json` |
| 6 | `transit_index.py` | `output/{line_to_cells,cell_to_lines}.json` |
| 7 | `render_pages.py` | `output/pages/NN.pdf` (map) + `NN_lines.pdf` (line grid) |
| 8 | `frontmatter.py` | cover + street index |
| 9 | `assemble.py` | `output/guiat.pdf` |

## Data and licenses

Code is MIT (`LICENSE`). All input data and the generated booklet are open,
attribution-only (no copyleft affects the printed booklet).

| Layer | Source | License |
|-------|--------|---------|
| AMBA bus routes | Min. de Transporte | CC-BY 4.0 |
| Subte GTFS | GCBA | CC-BY 2.5 AR |
| Street centerlines | GCBA | CC-BY 2.5 AR |
| Barrios | GCBA | CC-BY 2.5 AR |
| City blocks (manzanas) | GCBA | CC-BY 2.5 AR |
| Points of interest | OpenStreetMap | ODbL 1.0 |

ODbL's share-alike applies to derived databases, not to a produced work (a
printed booklet), which only needs to credit OpenStreetMap. So the booklet can
be distributed freely with attributions kept, and the code can be MIT.

Minimum attribution when redistributing the booklet:

> AMBA routes (Min. Transporte, CC-BY 4.0) · Subte / streets / barrios / blocks
> (GCBA, CC-BY 2.5 AR) · Points of interest © OpenStreetMap contributors (ODbL).

On the name: "Guía T" is a commercial name, so the project uses its own
(`Guía Abierta`, set in `config.yaml`).
