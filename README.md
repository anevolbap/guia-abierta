# Guía Abierta

Español · [English version](README.en.md)

Folleto **imprimible de bolsillo** (PDF), de código abierto, para desplazarse por Buenos
Aires en colectivo y subte, al estilo de la clásica Guía T. Se genera a partir
de datos abiertos y funciona de manera completamente offline: no incluye códigos
QR ni consultas en línea, el folleto es autosuficiente. ("Guía T" es un nombre
comercial; este proyecto utiliza un nombre propio, ver "Datos y licencias".)

El formato es vertical, tamaño bolsillo (121,7 × 190,5 mm), pensado para
imprimirse y plegarse como cuadernillo.

## Cómo se usa

1. Buscar la calle en el **índice de calles** y anotar la referencia, por
   ejemplo `12-C4` (página 12, celda C4).
2. Ir a la **página del mapa** 12 y ubicar la celda C4 (letras A–E en el eje
   horizontal, números 1–7 en el vertical).
3. Pasar a la **página contigua** (la grilla de líneas), que reproduce la misma
   cuadrícula. En la celda C4 figuran las líneas que pasan por ese sector: los
   números corresponden a colectivos y la letra de color, al subte.

Cada página de mapa va seguida de su grilla de líneas. Los mapas, de manera
deliberada, no trazan los recorridos de colectivo (serían unas 137 líneas
superpuestas, ilegibles); de eso se ocupa la grilla contigua. El subte sí se
dibuja en el mapa (seis líneas codificadas por color). Las manzanas se rellenan
en tono tierra, de modo que las calles quedan representadas por los espacios en
blanco.

## Instalación

```bash
uv venv --python 3.11
uv pip install -e .
```

WeasyPrint requiere bibliotecas del sistema (Pango, Cairo, GDK-PixBuf,
HarfBuzz). En Debian/Ubuntu:

```bash
sudo apt install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
                 libffi-dev libcairo2 libharfbuzz0b
```

GeoPandas, Fiona y pyproj se distribuyen con wheels binarios, de modo que no es
necesario instalar GDAL por separado.

## Uso

```bash
uv run python main.py            # pipeline completo -> output/guia-abierta.pdf
uv run python main.py --list     # lista las 9 etapas
uv run python main.py --only grid
uv run python main.py --from transit   # una etapa y las siguientes
```

`config.yaml` es la única fuente de verdad (escala, sub-grilla, título, alcance,
fuentes de datos). Con `mvp.enabled: true` el alcance se limita a un barrio,
para una prueba rápida; con `false` se genera toda la CABA (unas 26 páginas).

## Pipeline

| Etapa | Módulo | Salida |
|-------|--------|--------|
| 1 | `config.py` | CRS validado y geometría de página |
| 2 | `fetch.py` | descargas cacheadas en `data/` |
| 3 | `grid.py` | `data/grid.gpkg` (páginas y celdas) |
| 4 | `street_index.py` | `output/street_index.json` |
| 5 | `landmarks.py` | `output/landmarks.json` |
| 6 | `transit_index.py` | `output/{line_to_cells,cell_to_lines}.json` |
| 7 | `render_pages.py` | `output/pages/NN.pdf` (mapa) y `NN_lines.pdf` (grilla) |
| 8 | `frontmatter.py` | tapa e índice de calles |
| 9 | `assemble.py` | `output/guia-abierta.pdf` (PDF para leer) |
| 10 | `impose.py` | `output/guia-abierta-booklet.pdf` (2-up para imprimir) |

## Datos y licencias

El código se publica bajo licencia MIT (`LICENSE`). Todos los datos de entrada y
el folleto generado son abiertos y solo exigen atribución (ninguna licencia
copyleft afecta al folleto impreso).

| Capa | Fuente | Licencia |
|------|--------|----------|
| Recorridos de colectivos AMBA | Ministerio de Transporte | CC-BY 4.0 |
| Subte GTFS | GCBA | CC-BY 2.5 AR |
| Callejero | GCBA | CC-BY 2.5 AR |
| Barrios | GCBA | CC-BY 2.5 AR |
| Manzanas catastrales | GCBA | CC-BY 2.5 AR |
| Puntos de interés (POIs) | OpenStreetMap | ODbL 1.0 |

La ODbL incluye una cláusula "share-alike", pero se aplica a bases de datos
derivadas, no a una obra producida (un folleto impreso), que solo debe atribuir
a OpenStreetMap. Por eso el folleto puede distribuirse libremente manteniendo
las atribuciones, y el código puede ser MIT sin conflicto.

Atribución mínima para redistribuir el folleto:

> Recorridos AMBA (Min. Transporte, CC-BY 4.0) · Subte / Callejero / Barrios /
> Manzanas (GCBA, CC-BY 2.5 AR) · Puntos de interés © OpenStreetMap
> contributors (ODbL).

Sobre el nombre: "Guía T" es un nombre comercial, por eso el proyecto utiliza un
nombre propio (`Guía Abierta`, configurable en `config.yaml`).
