"""Cover + indices via WeasyPrint (HTML/CSS -> PDF).

Styled from design_handoff_guia_estilo/frontmatter.css (the "WeasyPrint
surface"). Pixel values are at the 460x720 px design reference, which is exactly
the booklet trim (121.71 x 190.5 mm @96dpi), so they port 1:1.

Builds: cover.pdf (cover + cómo usar), overview.pdf, street_index.pdf,
line_index.pdf.
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

# --------------------------------------------------------------------------
# design tokens + classes (ported from frontmatter.css)
# --------------------------------------------------------------------------
TOK = {
    "paper": "#F5F2EA", "panel": "#EDE7D8", "panel_border": "#DED7C6",
    "ink": "#1C1A15", "ink_deep": "#17150F", "cream": "#F1ECDF",
    "muted": "#8C877C", "muted2": "#9A9384", "body": "#5A554A",
    "accent": "#ED5B2A", "hairline": "#DAD3C4", "column_rule": "#E4DDCE",
}
SUBTE_HEX = {"A": "#34B6E4", "B": "#E2231A", "C": "#163F8C", "D": "#00925A",
             "E": "#6C3A93", "H": "#F4C500", "PM-C": "#00925A", "PM-S": "#00925A"}

DESIGN_CSS = f"""
{fonts.css_font_face()}
:root {{
  --paper:{TOK['paper']}; --panel:{TOK['panel']}; --panel-border:{TOK['panel_border']};
  --ink:{TOK['ink']}; --ink-deep:{TOK['ink_deep']}; --cream:{TOK['cream']};
  --muted:{TOK['muted']}; --muted-2:{TOK['muted2']}; --body:{TOK['body']};
  --accent:{TOK['accent']}; --hairline:{TOK['hairline']}; --column-rule:{TOK['column_rule']};
}}
* {{ box-sizing: border-box; }}
body {{ margin:0; font-family:"Public Sans", sans-serif; color:var(--ink); }}
.page {{ width:460px; height:720px; overflow:hidden; position:relative;
        page-break-after:always; background:var(--paper); }}
.kicker {{ font-size:11px; font-weight:700; letter-spacing:1.5px;
          text-transform:uppercase; color:var(--accent); }}

/* cover */
.cover {{ background:var(--ink-deep); color:var(--cream);
         padding:38px 34px 32px; display:flex; flex-direction:column;
         justify-content:space-between; }}
.cover__fishnet {{ position:absolute; inset:0; pointer-events:none;
  background-image:
    repeating-linear-gradient(90deg, rgba(237,91,42,.10) 0 1px, transparent 1px 20%),
    repeating-linear-gradient(0deg,  rgba(237,91,42,.08) 0 1px, transparent 1px 14.285%); }}
.cover__row {{ position:relative; display:flex; align-items:center; justify-content:space-between; }}
.cover__edmark {{ font-size:10px; letter-spacing:1.5px; color:#7C766A; }}
.cover__sub {{ font-size:13px; font-weight:600; letter-spacing:.5px; color:#A49C8A; margin-bottom:14px; }}
.cover__title {{ font-family:"Archivo Black"; font-size:88px; line-height:.84;
                letter-spacing:-3px; color:var(--cream); margin:0; position:relative; }}
.cover__rule {{ width:60px; height:5px; background:var(--accent); margin:24px 0 18px; position:relative; }}
.cover__tag {{ font-size:15px; line-height:1.45; color:#C9C2B1; max-width:300px; position:relative; }}
.cover__chips {{ display:flex; position:relative; }}
.cover__chips > * {{ margin-right:7px; }}
.chip {{ width:34px; height:34px; border-radius:7px; display:flex;
        align-items:center; justify-content:center;
        font-family:"Archivo Black"; font-size:16px; color:#fff; }}
.cover__foot {{ border-top:1px solid #2E2A20; padding-top:14px; display:flex;
               justify-content:space-between; align-items:flex-end; position:relative; }}
.cover__credits {{ font-size:9.5px; line-height:1.6; color:#7C766A; }}
.cover__scale {{ font-size:9.5px; line-height:1.5; color:#A49C8A; text-align:right; white-space:nowrap; }}

/* cómo usar */
.como {{ padding:40px 38px 30px; display:flex; flex-direction:column; height:720px; }}
.como__title {{ font-family:"Archivo Black"; font-size:40px; letter-spacing:-1.5px;
               line-height:1; color:var(--ink); margin:6px 0 0; }}
.rule {{ width:100%; height:1px; background:var(--hairline); margin:14px 0 22px; }}
.step {{ display:flex; margin-bottom:22px; }}
.step__n {{ flex:none; width:30px; height:30px; background:var(--ink-deep);
           color:var(--cream); font-family:"Archivo Black"; font-size:15px;
           display:flex; align-items:center; justify-content:center; margin-right:16px; }}
.step__t {{ font-size:16px; font-weight:700; color:var(--ink); margin-bottom:4px; }}
.step__d {{ font-size:13.5px; line-height:1.5; color:var(--body); }}
.como__inset {{ margin-top:auto; background:var(--panel); border:1px solid var(--panel-border);
               padding:18px; display:flex; align-items:center; }}
.minigrid {{ border-collapse:collapse; border:1px solid #C7BEA9; margin-right:18px; }}
.minigrid td {{ width:22px; height:22px; border:1px solid #C7BEA9; padding:0; }}
.minigrid td.hit {{ background:var(--accent); }}
.inset__cap {{ font-size:11px; color:var(--body); line-height:1.5; }}
.inset__cap b {{ font-family:"Archivo Black"; color:var(--ink-deep); font-weight:400; }}

/* índice (calles + líneas) */
.idx-head {{ margin-bottom:10px; }}
.idx-sub {{ font-size:11px; color:var(--muted); margin-top:2px; }}
.indice__cols {{ column-count:2; column-gap:26px; column-rule:1px solid var(--column-rule); }}
.grp {{ font-family:"Archivo Black"; font-size:30px; line-height:.9; color:var(--ink-deep);
        margin:8px 0 4px; break-inside:avoid; break-after:avoid; }}
.entry {{ break-inside:avoid; margin-bottom:6px; line-height:1.25; }}
.entry__name {{ font-size:11.5px; font-weight:600; color:var(--ink); }}
.ref {{ font-size:10.5px; white-space:nowrap; margin-right:4px; }}
.ref__p {{ font-weight:700; color:var(--accent); }}
.ref__c {{ color:var(--muted-2); }}
.lrow {{ break-inside:avoid; margin-bottom:7px; line-height:1.3; }}
.lbadge {{ font-family:"Archivo Black"; font-size:12px; border-radius:4px;
          padding:1px 6px; margin-right:6px; color:#fff; }}
.lroute {{ font-size:10px; color:var(--body); }}
img.overview {{ width:100%; }}
"""


def _render(body: str, out_name: str, page_rule: str):
    doc = (f"<html><head><meta charset='utf-8'><style>{page_rule}{DESIGN_CSS}"
           f"</style></head><body>{body}</body></html>")
    out = CFG.output_dir / out_name
    HTML(string=doc).write_pdf(out)
    print(f"[frontmatter] {out.name}")
    return out


PAGE_FIXED = "@page { size: 460px 720px; margin: 0; }"
PAGE_FLOW = "@page { size: 460px 720px; margin: 34px 30px 26px; background: " + TOK["paper"] + "; }"


# --------------------------------------------------------------------------
# matplotlib helper: page overview
# --------------------------------------------------------------------------
def make_overview_png() -> str:
    pages = load_grid()["pages"]
    boundary = load_boundary()
    fig, ax = plt.subplots(figsize=(CFG.mm_to_in(100), CFG.mm_to_in(150)))
    boundary.plot(ax=ax, color=TOK["panel"], edgecolor=TOK["muted"], lw=0.6)
    pages.boundary.plot(ax=ax, color=TOK["accent"], lw=0.6)
    for _, p in pages.iterrows():
        c = p.geometry.centroid
        ax.text(c.x, c.y, str(int(p["page"])), ha="center", va="center",
                fontsize=6, fontfamily="Archivo Black", color=TOK["accent"])
    ax.set_axis_off()
    ax.set_aspect("equal")
    out = CFG.output_dir / "overview.png"
    fig.savefig(out, dpi=200, transparent=True, bbox_inches="tight")
    plt.close(fig)
    return out.as_uri()


# --------------------------------------------------------------------------
# cover + cómo usar
# --------------------------------------------------------------------------
def _minigrid_html() -> str:
    """5x7 cell grid (A-E / 1-7) with C4 filled, as a table (WeasyPrint has no
    CSS grid)."""
    rows = []
    for r in range(7):
        cells = "".join(
            f"<td class='hit'></td>" if (r == 3 and c == 2) else "<td></td>"
            for c in range(5))
        rows.append(f"<tr>{cells}</tr>")
    return f"<table class='minigrid'>{''.join(rows)}</table>"


def cover():
    title_html = "<br>".join(escape(w) for w in CFG.title.split())
    scale_str = f"{int(CFG.scale_denom):,}".replace(",", " ")
    chips = "".join(
        f"<div class='chip' style='background:{SUBTE_HEX[k]};"
        f"{'color:#1C1A15' if k == 'H' else ''}'>{k}</div>"
        for k in ("A", "B", "C", "D", "E", "H"))
    cover_html = f"""
    <div class='page cover'>
      <div class='cover__fishnet'></div>
      <div class='cover__row'>
        <div class='kicker'>{escape(CFG.edition)}</div>
        <div class='cover__edmark'>v{escape(CFG.datos_fecha)}</div>
      </div>
      <div>
        <h1 class='cover__title'>{title_html}</h1>
        <div class='cover__rule'></div>
        <div class='cover__tag'>{escape(CFG.subtitle)}. Mapas, índice de calles
          y líneas de colectivo y subte, hechos con datos abiertos.</div>
      </div>
      <div class='cover__chips'>{chips}</div>
      <div class='cover__foot'>
        <div class='cover__credits'>
          Recorridos AMBA · Min. Transporte (CC-BY 4.0)<br>
          Subte / Callejero / Barrios / Manzanas · GCBA (CC-BY 2.5 AR)<br>
          Puntos de interés · © OpenStreetMap (ODbL)<br>
          Software libre · código MIT
        </div>
        <div class='cover__scale'>Escala 1:{scale_str}<br>EPSG:9498</div>
      </div>
    </div>"""

    como_html = f"""
    <div class='page como'>
      <div class='kicker'>{escape(CFG.title)}</div>
      <h1 class='como__title'>Cómo usar</h1>
      <div class='rule'></div>
      <div class='step'><div class='step__n'>1</div><div>
        <div class='step__t'>Buscá la calle</div>
        <div class='step__d'>En el <b>índice de calles</b>, anotá la referencia,
          por ejemplo <b>12-C4</b> (página 12, celda C4).</div></div></div>
      <div class='step'><div class='step__n'>2</div><div>
        <div class='step__t'>Andá al mapa</div>
        <div class='step__d'>Página 12, celda C4: letras A–E arriba, números 1–7
          al costado.</div></div></div>
      <div class='step'><div class='step__n'>3</div><div>
        <div class='step__t'>Leé las líneas</div>
        <div class='step__d'>La página de al lado repite la cuadrícula. En C4
          están las líneas: número = colectivo, letra de color = subte.</div></div></div>
      <div class='como__inset'>
        {_minigrid_html()}
        <div class='inset__cap'>Misma grilla en el mapa y en las líneas.<br>
          Referencia <b>12-C4</b>.</div>
      </div>
    </div>"""
    return _render(cover_html + como_html, "cover.pdf", PAGE_FIXED)


def overview():
    uri = make_overview_png()
    body = f"""
    <div class='idx-head'><div class='kicker'>Guía Abierta</div>
      <div class='idx-sub'>Mapa índice — número de página por zona</div></div>
    <img class='overview' src='{uri}'>"""
    return _render(body, "overview.pdf", PAGE_FLOW)


# --------------------------------------------------------------------------
# street index
# --------------------------------------------------------------------------
def _first_letter(name: str) -> str:
    for ch in name:
        if ch.isalpha():
            return "Ñ" if ch.lower() == "ñ" else unicodedata.normalize("NFD", ch)[0].upper()
    return "#"


def _ref_html(ref: str) -> str:
    page, cell = ref.split("-")
    return f"<span class='ref'><span class='ref__p'>{page}</span><span class='ref__c'>-{cell}</span></span>"


def street_index_pdf():
    data = json.loads((CFG.output_dir / "street_index.json").read_text(encoding="utf-8"))
    parts, cur = [], None
    for e in data["entries"]:
        letter = _first_letter(e["name"])
        if letter != cur:
            cur = letter
            parts.append(f"<div class='grp'>{escape(letter)}</div>")
        rng = f" <span class='ref__c'>{e['range']}</span>" if e.get("range") else ""
        refs = "".join(_ref_html(r) for r in e["refs"])
        parts.append(f"<div class='entry'><span class='entry__name'>"
                     f"{escape(e['name'])}</span>{rng} {refs}</div>")
    head = ("<div class='idx-head'><div class='kicker'>Índice de calles</div>"
            "<div class='idx-sub'>calle · página-celda</div></div>")
    body = head + f"<div class='indice__cols'>{''.join(parts)}</div>"
    return _render(body, "street_index.pdf", PAGE_FLOW)


# --------------------------------------------------------------------------
# line index (colectivos + subte), per-line colored badges + street route
# --------------------------------------------------------------------------
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


def _line_route(ln):
    streets = ln.get("streets") or []
    return ", ".join(streets) if streets else ", ".join(_line_cells(ln))


def _color_overrides() -> dict:
    import csv
    p = CFG.data_dir / "line_colors.csv"
    out = {}
    if p.exists():
        for row in csv.reader(p.read_text(encoding="utf-8").splitlines()):
            if len(row) >= 2 and row[1].strip().startswith("#"):
                out[row[0].strip()] = row[1].strip()
    return out


def _line_bg(line, overrides):
    if str(line) in overrides:
        return overrides[str(line)]
    import colorsys
    import zlib
    s = str(line)
    seed = int(s) if s.isdigit() else zlib.crc32(s.encode())
    h = ((seed * 137) % 360) / 360.0
    r, g, b = colorsys.hls_to_rgb(h, 0.46, 0.55)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def _text_on(bg):
    r, g, b = int(bg[1:3], 16), int(bg[3:5], 16), int(bg[5:7], 16)
    return "#1C1A15" if (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.62 else "#fff"


def line_index_pdf():
    data = json.loads((CFG.output_dir / "line_to_cells.json").read_text(encoding="utf-8"))
    colect = sorted((l for l in data["lines"] if l["mode"] == "colectivo"),
                    key=lambda l: _line_key(l["line"]))
    subte = sorted((l for l in data["lines"] if l["mode"] == "subte"),
                   key=lambda l: _line_key(l["line"]))
    ov = _color_overrides()

    def row(ln, bg):
        fg = _text_on(bg)
        return (f"<div class='lrow'><span class='lbadge' style='background:{bg};"
                f"color:{fg}'>{escape(str(ln['line']))}</span>"
                f"<span class='lroute'>{escape(_line_route(ln))}</span></div>")

    crows = "".join(row(l, _line_bg(l["line"], ov)) for l in colect)
    srows = "".join(row(l, SUBTE_HEX.get(str(l["line"]).upper(), "#444")) for l in subte)
    head = ("<div class='idx-head'><div class='kicker'>Líneas de colectivo</div>"
            "<div class='idx-sub'>línea · recorrido por calles</div></div>")
    shead = "<div class='idx-head'><div class='kicker'>Subte</div></div>"
    body = (head + f"<div class='indice__cols'>{crows}</div>"
            + shead + f"<div class='indice__cols'>{srows}</div>")
    return _render(body, "line_index.pdf", PAGE_FLOW)


def build_frontmatter() -> list:
    return [cover(), overview(), street_index_pdf(), line_index_pdf()]


if __name__ == "__main__":
    build_frontmatter()
