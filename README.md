# Guía T Remake

Open-source, printable A5 PDF booklet for navigating Buenos Aires by colectivo
and subte, in the style of the classic Guía T. Generated from open data,
offline-final (no QR codes, no live lookups: the booklet is self-sufficient).

It replicates the way the original Guía T is used:

1. Look up your street in the **street index**, get a cell reference like
   `12-C4` (page 12, cell C4).
2. Turn to **map page 12** and find cell C4 (letters A-E across, numbers 1-7
   down).
3. Flip to the **facing page** (12 · líneas): same grid, and cell C4 lists the
   lines passing through it. Numbers are colectivos, a coloured letter is the
   subte.

Every map page is followed by its line-grid page. Map pages deliberately do
**not** draw colectivo routes (137 lines would be spaghetti); the facing
line-grid carries that. Subte is the exception: 6 colour-coded lines, drawn on
the map too. A line index at the back does the reverse lookup (line -> cells).

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

GeoPandas/Fiona/pyproj ship binary wheels, so GDAL does not need a separate
system install.

## Run

```bash
uv run python main.py            # full pipeline -> output/guiat.pdf
uv run python main.py --list     # show the 9 stages
uv run python main.py --only grid
uv run python main.py --from transit   # a stage and everything after
```

The default `config.yaml` runs in **MVP mode**: scoped to one barrio
(`CHACARITA`) with a 6-page cap, to prove the full round-trip cheaply. Set
`mvp.enabled: false` for a full-CABA run.

## Pipeline

| Stage | Module | Output |
|-------|--------|--------|
| 1 | `config.py` | validated CRS + derived page geometry |
| 2 | `fetch.py` | cached downloads in `data/` |
| 3 | `grid.py` | `data/grid.gpkg` (pages + cells) |
| 4 | `street_index.py` | `output/street_index.json` |
| 5 | `landmarks.py` | `output/landmarks.json` |
| 6 | `transit_index.py` | `output/line_to_cells.json`, `output/cell_to_lines.json` |
| 7 | `render_pages.py` | `output/pages/NN.pdf` (map) + `NN_lines.pdf` (line grid) |
| 8 | `frontmatter.py` | cover + index PDFs |
| 9 | `assemble.py` | `output/guiat.pdf` |

`config.yaml` is the single source of truth. Change scale, sub-grid, MVP scope,
and data sources there.

## Data + licenses

- Colectivos: AMBA *Recorridos de servicios de colectivos* (Min. Transporte),
  CC-BY 4.0. Geometry-only, clipped to CABA. This is the full ~137-line feed,
  not the ~27-line city GTFS.
- Subte / Callejero / Barrios: GCBA open data.
- Landmarks: © OpenStreetMap contributors, ODbL.

Both attributions are printed on every map page and on the cover. Code is MIT;
no AGPL obligation (OCitySMap is not a dependency).

See `DECISIONS.md` for the design rationale and every baked-in choice.
