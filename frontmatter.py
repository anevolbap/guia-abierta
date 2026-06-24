"""Cover + indices as A5 PDFs via WeasyPrint (HTML/CSS -> PDF).

Builds:
  cover.pdf            title + attribution + datos-fecha colophon
  overview.pdf         barrios overview with the page-number grid
  street_index.pdf     alphabetical streets -> cell refs (multi-column)
  line_index.pdf       colectivo + subte lines -> ordered cells
  landmark_index.pdf   landmarks -> cell refs, grouped by category
"""
from __future__ import annotations

import json
from html import escape

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from weasyprint import HTML

from config import CFG
from grid import load_boundary, load_grid

PAGE_CSS = f"""
@page {{ size: {CFG.page_w_mm}mm {CFG.page_h_mm}mm; margin: 12mm 10mm; }}
* {{ font-family: 'DejaVu Sans', sans-serif; }}
body {{ font-size: 8.5pt; color: #111; }}
h1 {{ font-size: 20pt; margin: 0 0 4mm; }}
h2 {{ font-size: 12pt; border-bottom: 1px solid #444; padding-bottom: 1mm;
      margin: 4mm 0 2mm; }}
.cols {{ column-count: 3; column-gap: 5mm; }}
.cols2 {{ column-count: 2; column-gap: 5mm; }}
.entry {{ break-inside: avoid; margin: 0 0 0.6mm; line-height: 1.25; }}
.name {{ font-weight: bold; }}
.refs {{ color: #333; }}
.muted {{ color: #666; font-size: 7.5pt; }}
.cover {{ text-align: center; margin-top: 40mm; }}
.badge {{ display: inline-block; width: 5mm; height: 5mm; border-radius: 50%;
          text-align: center; color: #fff; font-weight: bold; }}
img.overview {{ width: 100%; }}
"""


def _render(html_body: str, out_name: str):
    doc = f"<html><head><meta charset='utf-8'><style>{PAGE_CSS}</style></head>" \
          f"<body>{html_body}</body></html>"
    out = CFG.output_dir / out_name
    HTML(string=doc).write_pdf(out)
    print(f"[frontmatter] {out.name}")
    return out


def make_overview_png() -> str:
    grid = load_grid()
    pages = grid["pages"]
    boundary = load_boundary()
    fig, ax = plt.subplots(figsize=(CFG.mm_to_in(128), CFG.mm_to_in(170)))
    boundary.plot(ax=ax, color="#eef2f0", edgecolor="#888", lw=0.6)
    pages.boundary.plot(ax=ax, color="#c0392b", lw=0.5)
    for _, p in pages.iterrows():
        c = p.geometry.centroid
        ax.text(c.x, c.y, str(int(p["page"])), ha="center", va="center",
                fontsize=6, weight="bold", color="#c0392b")
    ax.set_axis_off()
    ax.set_aspect("equal")
    out = CFG.output_dir / "overview.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out.as_uri()


def cover():
    body = f"""
    <div class='cover'>
      <h1>Guía T</h1>
      <p style='font-size:12pt'>Buenos Aires · colectivos y subte</p>
      <p class='muted'>Edición open data · datos a fecha {escape(CFG.datos_fecha)}</p>
      <p class='muted' style='margin-top:30mm'>
        Recorridos AMBA (Min. Transporte, CC-BY 4.0) ·
        Subte/Callejero/Barrios (GCBA) ·
        Puntos de interés © OpenStreetMap contributors (ODbL).<br>
        Generado con software libre. Escala 1:{int(CFG.scale_denom)}.
      </p>
    </div>
    <div style='page-break-before: always'>
      <h2>Cómo usar</h2>
      <ol style='font-size:9.5pt; line-height:1.5'>
        <li>Buscá tu calle en el <b>índice de calles</b>. Anotá la referencia,
            por ejemplo <b>12-C4</b> (página 12, celda C4).</li>
        <li>Andá a la <b>página del mapa</b> 12 y ubicá la celda C4 con las
            letras (A-E) arriba y los números (1-7) al costado.</li>
        <li>Pasá a la <b>página siguiente</b> (12 · líneas): tiene la misma
            grilla. Leé la celda C4 y vas a ver las líneas que pasan por ahí.
            Los números son colectivos; la letra de color es el subte.</li>
      </ol>
      <p class='muted'>Cada mapa va seguido de su grilla de líneas. El índice de
      líneas (al final) hace el camino inverso: de una línea a sus celdas.</p>
    </div>"""
    return _render(body, "cover.pdf")


def overview():
    uri = make_overview_png()
    body = f"<h2>Mapa índice de páginas</h2><img class='overview' src='{uri}'>"
    return _render(body, "overview.pdf")


def street_index_pdf():
    data = json.loads((CFG.output_dir / "street_index.json").read_text(encoding="utf-8"))
    def row(e):
        rng = f" <span class='muted'>{e['range']}</span>" if e.get("range") else ""
        return (f"<div class='entry'><span class='name'>{escape(e['name'])}</span>{rng} "
                f"<span class='refs'>{', '.join(e['refs'])}</span></div>")
    rows = "".join(row(e) for e in data["entries"])
    body = f"<h2>Índice de calles</h2><div class='cols'>{rows}</div>"
    return _render(body, "street_index.pdf")


def line_index_pdf():
    data = json.loads((CFG.output_dir / "line_to_cells.json").read_text(encoding="utf-8"))
    by_mode = {"colectivo": [], "subte": []}
    for ln in data["lines"]:
        by_mode.setdefault(ln["mode"], []).append(ln)
    sections = []
    titles = {"colectivo": "Colectivos", "subte": "Subte"}
    for mode in ("colectivo", "subte"):
        rows = []
        for ln in by_mode.get(mode, []):
            for dname, refs in ln["directions"].items():
                tag = "" if dname == "merged" else f" <span class='muted'>({dname})</span>"
                rows.append(
                    f"<div class='entry'><span class='name'>{escape(str(ln['line']))}</span>{tag} "
                    f"<span class='refs'>{', '.join(refs)}</span></div>")
        if rows:
            sections.append(f"<h2>{titles[mode]}</h2><div class='cols2'>{''.join(rows)}</div>")
    return _render("".join(sections), "line_index.pdf")


def landmark_index_pdf():
    data = json.loads((CFG.output_dir / "landmarks.json").read_text(encoding="utf-8"))
    by_cat: dict[str, list] = {}
    for e in data["entries"]:
        by_cat.setdefault(e["category"], []).append(e)
    sections = []
    for cat in sorted(by_cat):
        rows = "".join(
            f"<div class='entry'><span class='name'>{escape(e['name'])}</span> "
            f"<span class='refs'>{e['ref']}</span></div>"
            for e in sorted(by_cat[cat], key=lambda x: x["name"]))
        sections.append(f"<h2>{escape(cat)}</h2><div class='cols'>{rows}</div>")
    return _render("".join(sections), "landmark_index.pdf")


def build_frontmatter() -> list:
    out = [cover(), overview(), street_index_pdf(), line_index_pdf()]
    if (CFG.output_dir / "landmarks.json").exists():
        out.append(landmark_index_pdf())
    return out


if __name__ == "__main__":
    build_frontmatter()
