# Guía Bondi

Español · [English version](README.en.md)

Folleto **A5 imprimible** (PDF) de código abierto para moverte por Buenos Aires
en colectivo y subte, al estilo de la clásica Guía T. Se arma con datos
abiertos y es 100% offline: no tiene códigos QR ni consultas online, el folleto
se vale solo. ("Guía T" es un nombre comercial; este proyecto usa un nombre
propio, ver `DATA.md`.)

Es A5 vertical (148 × 210 mm), pensado para imprimir como guía de bolsillo.

## Cómo se usa (el método Guía T)

1. Buscá tu calle en el **índice de calles** y anotá la referencia, por ejemplo
   `12-C4` (página 12, celda C4).
2. Andá a la **página del mapa** 12 y ubicá la celda C4 (letras A–E arriba,
   números 1–7 al costado).
3. Pasá a la **página de al lado** (la grilla de líneas): es la misma
   cuadrícula. Leé la celda C4 y vas a ver las líneas que pasan por ahí. Los
   números son colectivos; la letra de color es el subte.

Cada página de mapa va seguida de su grilla de líneas. Los mapas a propósito
**no** dibujan los recorridos de colectivo (serían ~137 líneas, un despelote);
de eso se encarga la grilla de al lado. El subte sí va en el mapa (6 líneas con
color). Las manzanas van rellenas en tono tierra, así las calles quedan como los
huecos blancos.

## Instalación

```bash
uv venv --python 3.11
uv pip install -e .
```

WeasyPrint necesita librerías del sistema (Pango, Cairo, GDK-PixBuf, HarfBuzz).
En Debian/Ubuntu:

```bash
sudo apt install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
                 libffi-dev libcairo2 libharfbuzz0b
```

GeoPandas/Fiona/pyproj traen wheels binarios, así que GDAL no hace falta
instalarlo aparte.

## Uso

```bash
uv run python main.py            # pipeline completo -> output/guiat.pdf
uv run python main.py --list     # lista las 9 etapas
uv run python main.py --only grid
uv run python main.py --from transit   # una etapa y todo lo que sigue
```

`config.yaml` es la única fuente de verdad (escala, sub-grilla, título, alcance,
fuentes de datos). Con `mvp.enabled: true` se limita a un barrio para una prueba
rápida; con `false` arma toda la CABA (~26 páginas).

## Pipeline

| Etapa | Módulo | Salida |
|-------|--------|--------|
| 1 | `config.py` | CRS validado + geometría de página |
| 2 | `fetch.py` | descargas cacheadas en `data/` |
| 3 | `grid.py` | `data/grid.gpkg` (páginas + celdas) |
| 4 | `street_index.py` | `output/street_index.json` |
| 5 | `landmarks.py` | `output/landmarks.json` |
| 6 | `transit_index.py` | `output/{line_to_cells,cell_to_lines}.json` |
| 7 | `render_pages.py` | `output/pages/NN.pdf` (mapa) + `NN_lines.pdf` (grilla) |
| 8 | `frontmatter.py` | tapa + índice de calles |
| 9 | `assemble.py` | `output/guiat.pdf` |

## Datos y licencias

El código va con licencia MIT (`LICENSE`). Todos los datos de entrada y el
folleto generado son abiertos, solo piden atribución. La tabla completa y el
texto de atribución están en `DATA.md`. Las decisiones de diseño, en
`DECISIONS.md`.
