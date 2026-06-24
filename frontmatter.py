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
import unicodedata
from html import escape

import matplotlib

matplotlib.use("Agg")
import fonts  # noqa: E402  registers bundled fonts for matplotlib
import matplotlib.pyplot as plt
from weasyprint import HTML

from config import CFG
from grid import load_boundary, load_grid

PAGE_CSS = f"""
{fonts.css_font_face()}
@page {{ size: {CFG.page_w_mm}mm {CFG.page_h_mm}mm; margin: 12mm 10mm; }}
* {{ font-family: '{fonts.BODY}', sans-serif; }}
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
/* street index: dense columns with big letter dividers (Guía T calles) */
.idxcols {{ column-count: 4; column-gap: 4mm; }}
.grp {{ break-inside: avoid; font-family: '{fonts.DISPLAY}'; font-size: 14pt;
        color: #fff; background: #0e3d52; border-radius: 1.5mm;
        padding: 0.3mm 2mm; margin: 2.5mm 0 1mm; display: inline-block; }}
.st {{ break-inside: avoid; font-size: 7pt; line-height: 1.18; margin: 0 0 0.3mm; }}
.st b {{ font-weight: bold; }}
/* line index: bold number badges (Guía T bondis) */
.linecols {{ column-count: 2; column-gap: 6mm; }}
.lrow {{ break-inside: avoid; margin: 0 0 1.5mm; line-height: 1.2; }}
.lbadge {{ display: inline-block; font-family: '{fonts.DISPLAY}'; font-size: 9.5pt;
           border: 1pt solid #111; border-radius: 1.5mm; padding: 0.2mm 1.6mm;
           margin-right: 1.6mm; }}
.sbadge {{ display: inline-block; min-width: 4mm; text-align: center; font-size: 9pt;
           font-weight: bold; color: #fff; border-radius: 1.2mm; padding: 0.2mm 1.6mm;
           margin-right: 1.6mm; }}
.lcells {{ font-size: 6.5pt; color: #333; }}
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


def make_silhouette_png() -> str:
    """White CABA silhouette on transparent bg, for the cover watermark."""
    fig, ax = plt.subplots(figsize=(CFG.mm_to_in(150), CFG.mm_to_in(170)))
    load_boundary().plot(ax=ax, color="white", edgecolor="none")
    ax.set_axis_off()
    ax.set_aspect("equal")
    out = CFG.output_dir / "silhouette.png"
    fig.savefig(out, dpi=200, transparent=True, bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    return out.as_uri()


SUBTE_STRIPE = ["#38b6ff", "#e30613", "#005aab", "#009b3a", "#6d2c91", "#ffd200"]


def cover():
    sil = make_silhouette_png()
    stripe = "".join(f"<span style='background:{c}'></span>" for c in SUBTE_STRIPE)
    w, h = CFG.page_w_mm, CFG.page_h_mm
    css = f"""
    {fonts.css_font_face()}
    @page cover {{ size: {w}mm {h}mm; margin: 0; }}
    @page {{ size: {w}mm {h}mm; margin: 14mm 12mm; }}
    * {{ font-family: '{fonts.BODY}', sans-serif; }}
    .cv {{ page: cover; position: relative; width: {w}mm; height: {h}mm;
           overflow: hidden; color: #fff;
           background: linear-gradient(155deg, #0e3d52 0%, #0a2433 100%); }}
    .cv img {{ position: absolute; right: -28mm; bottom: -16mm; width: 165mm;
               opacity: 0.10; }}
    .kicker {{ position: absolute; top: 20mm; left: 14mm; font-size: 9pt;
               letter-spacing: 4px; text-transform: uppercase; color: #bfe0e8; }}
    .title {{ position: absolute; top: 52mm; left: 13mm; font-size: 46pt;
              font-family: '{fonts.DISPLAY}', sans-serif; line-height: 0.95; }}
    .sub {{ position: absolute; top: 96mm; left: 14mm; font-size: 13pt;
            color: #dceef2; }}
    .stripe {{ position: absolute; top: 112mm; left: 14mm; }}
    .stripe span {{ display: inline-block; width: 14mm; height: 5mm;
                    margin-right: 1.5mm; border-radius: 1mm; }}
    .meta {{ position: absolute; top: 124mm; left: 14mm; font-size: 9pt;
             color: #9fc3cf; }}
    .foot {{ position: absolute; bottom: 13mm; left: 14mm; right: 14mm;
             font-size: 7pt; color: #88abb6; line-height: 1.55; }}
    h2 {{ font-size: 13pt; border-bottom: 1px solid #444; padding-bottom: 1mm;
          margin: 0 0 3mm; }}
    ol {{ font-size: 10pt; line-height: 1.55; padding-left: 6mm; }}
    .note {{ color: #666; font-size: 8pt; margin-top: 3mm; }}
    """
    body = f"""
    <div class='cv'>
      <img src='{sil}'>
      <div class='kicker'>{escape(CFG.edition)}</div>
      <div class='title'>{escape(CFG.title)}</div>
      <div class='sub'>{escape(CFG.subtitle)}</div>
      <div class='stripe'>{stripe}</div>
      <div class='meta'>Escala 1:{int(CFG.scale_denom)} · datos {escape(CFG.datos_fecha)}</div>
      <div class='foot'>
        Recorridos AMBA (Min. Transporte, CC-BY 4.0) ·
        Subte / Callejero / Barrios / Manzanas (GCBA) ·
        Puntos de interés © OpenStreetMap contributors (ODbL).<br>
        Hecho con software libre. Licencia del código: MIT.
      </div>
    </div>
    <div style='page-break-before: always'>
      <h2>Cómo usar</h2>
      <ol>
        <li>Buscá tu calle en el <b>índice de calles</b>. Anotá la referencia,
            por ejemplo <b>12-C4</b> (página 12, celda C4).</li>
        <li>Andá a la <b>página del mapa</b> 12 y ubicá la celda C4 con las
            letras (A-E) arriba y los números (1-7) al costado.</li>
        <li>Pasá a la <b>página de al lado</b> (la grilla de líneas): tiene la
            misma cuadrícula. Leé la celda C4 y vas a ver las líneas que pasan
            por ahí. Los números son colectivos; la letra de color es el subte.</li>
      </ol>
      <p class='note'>Cada mapa va seguido de su grilla de líneas.</p>
    </div>"""
    doc = f"<html><head><meta charset='utf-8'><style>{css}</style></head><body>{body}</body></html>"
    out = CFG.output_dir / "cover.pdf"
    HTML(string=doc).write_pdf(out)
    print(f"[frontmatter] {out.name}")
    return out


def overview():
    uri = make_overview_png()
    body = f"<h2>Mapa índice de páginas</h2><img class='overview' src='{uri}'>"
    return _render(body, "overview.pdf")


def _first_letter(name: str) -> str:
    for ch in name:
        if ch.isalpha():
            if ch.lower() == "ñ":
                return "Ñ"
            return unicodedata.normalize("NFD", ch)[0].upper()
    return "#"


def street_index_pdf():
    data = json.loads((CFG.output_dir / "street_index.json").read_text(encoding="utf-8"))
    parts, cur = [], None
    for e in data["entries"]:
        letter = _first_letter(e["name"])
        if letter != cur:
            cur = letter
            parts.append(f"<div class='grp'>{escape(letter)}</div>")
        rng = f" <span class='muted'>{e['range']}</span>" if e.get("range") else ""
        parts.append(f"<div class='st'><b>{escape(e['name'])}</b>{rng} "
                     f"<span class='refs'>{', '.join(e['refs'])}</span></div>")
    body = f"<h2>Índice de calles</h2><div class='idxcols'>{''.join(parts)}</div>"
    return _render(body, "street_index.pdf")


SUBTE_HEX = {"A": "#38b6ff", "B": "#e30613", "C": "#005aab", "D": "#009b3a",
             "E": "#6d2c91", "H": "#ffd200", "PM-C": "#00a651", "PM-S": "#00a651"}


def _ref_key(ref):
    page, cell = ref.split("-")
    return (int(page), cell[0], int(cell[1:]))


def _line_key(line):
    return (0, int(line)) if str(line).isdigit() else (1, str(line))


def _line_cells(ln):
    seen = set()
    for refs in ln["directions"].values():
        seen.update(refs)
    return sorted(seen, key=_ref_key)


def line_index_pdf():
    data = json.loads((CFG.output_dir / "line_to_cells.json").read_text(encoding="utf-8"))
    colect = sorted((l for l in data["lines"] if l["mode"] == "colectivo"),
                    key=lambda l: _line_key(l["line"]))
    subte = sorted((l for l in data["lines"] if l["mode"] == "subte"),
                   key=lambda l: _line_key(l["line"]))

    crows = "".join(
        f"<div class='lrow'><span class='lbadge'>{escape(str(l['line']))}</span>"
        f"<span class='lcells'>{', '.join(_line_cells(l))}</span></div>"
        for l in colect)
    srows = "".join(
        f"<div class='lrow'><span class='sbadge' style='background:"
        f"{SUBTE_HEX.get(str(l['line']).upper(), '#444')}'>{escape(str(l['line']))}</span>"
        f"<span class='lcells'>{', '.join(_line_cells(l))}</span></div>"
        for l in subte)
    body = (f"<h2>Líneas de colectivo</h2><div class='linecols'>{crows}</div>"
            f"<h2>Subte</h2><div class='linecols'>{srows}</div>")
    return _render(body, "line_index.pdf")


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
    # Landmark index stays off (map markers cover it). Re-enable if needed:
    # if (CFG.output_dir / "landmarks.json").exists():
    #     out.append(landmark_index_pdf())
    return out


if __name__ == "__main__":
    build_frontmatter()
