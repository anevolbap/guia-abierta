"""Cover + indices via WeasyPrint (HTML/CSS -> PDF).

Styled from design_handoff_guia_estilo (the "WeasyPrint surface"): light
"porteña" cover, cómo-usar with a gutter mini-grid, 4-column grouped street
index, and a line-art colectivo line index (pentagon route sign + bus
illustration). Pixel values are at the 460x720 px design reference, which is
exactly the booklet trim (121.71 x 190.5 mm @96dpi), so they port 1:1.

Builds: cover.pdf (cover + cómo usar), overview.pdf, street_index.pdf,
line_index.pdf.
"""
from __future__ import annotations

import colorsys
import json
import unicodedata
import zlib
from html import escape

import matplotlib

matplotlib.use("Agg")
import fonts  # noqa: E402  registers bundled fonts for matplotlib
import matplotlib.pyplot as plt
from weasyprint import HTML

from config import CFG
from grid import load_boundary, load_grid

NBSP = " "

# --------------------------------------------------------------------------
# design tokens
# --------------------------------------------------------------------------
TOK = {
    "paper": "#F5F2EA", "panel": "#EDE7D8", "panel_border": "#DED7C6",
    "ink": "#1C1A15", "ink_deep": "#17150F", "cream": "#F1ECDF",
    "muted": "#8C877C", "muted2": "#9A9384", "body": "#5A554A",
    "accent": "#ED5B2A", "hairline": "#DAD3C4", "column_rule": "#E4DDCE",
}
SUBTE_HEX = {"A": "#34B6E4", "B": "#E2231A", "C": "#163F8C", "D": "#00925A",
             "E": "#6C3A93", "H": "#F4C500"}
TREN = [("Mitre", "#16A085"), ("Sarmiento", "#E8552D"), ("Roca", "#1F5FB0"),
        ("San Martín", "#C0392B"), ("Belgrano N", "#2E9E4B"),
        ("Belgrano S", "#7E3F98"), ("Urquiza", "#E8902B")]

# Representative liveries (roof, stripe) from the handoff. Others synthesized.
LIVERY = {
    "15": ("#15448F", "#E2231A"), "19": ("#1E7A3E", "#F4C20D"),
    "29": ("#B11E2A", "#E8902B"), "60": ("#16306B", "#C8202A"),
    "107": ("#E8702A", "#15346B"), "114": ("#00838F", "#F4C20D"),
    "130": ("#1F3A6E", "#E8902B"), "133": ("#1E7A46", "#C8202A"),
    "152": ("#15346B", "#C8202A"), "160": ("#7A1F2B", "#E8B23A"),
    "166": ("#5E3A8C", "#F4C20D"), "168": ("#0E7C7B", "#E8902B"),
}
GLASS = "#BFD8E0"

# --------------------------------------------------------------------------
# CSS for the data-driven index pages (cover + cómo-usar are inline-styled)
# --------------------------------------------------------------------------
DESIGN_CSS = f"""
{fonts.css_font_face()}
:root {{
  --paper:{TOK['paper']}; --panel:{TOK['panel']}; --panel-border:{TOK['panel_border']};
  --ink:{TOK['ink']}; --ink-deep:{TOK['ink_deep']}; --cream:{TOK['cream']};
  --muted:{TOK['muted']}; --muted-2:{TOK['muted2']}; --body:{TOK['body']};
  --accent:{TOK['accent']}; --hairline:{TOK['hairline']}; --column-rule:{TOK['column_rule']};
}}
* {{ box-sizing: border-box; }}
body {{ margin:0; font-family:"Public Sans", sans-serif; color:var(--ink); -weasy-hyphens:none; }}
.page {{ width:460px; height:720px; overflow:hidden; position:relative;
        page-break-after:always; }}
.kicker {{ font-size:11px; font-weight:700; letter-spacing:1.5px;
          text-transform:uppercase; color:var(--accent); }}
.nw {{ white-space:nowrap; }}

/* shared index header */
.idx-head {{ display:flex; align-items:flex-start; justify-content:space-between; }}
.idx-sub {{ font-size:10.5px; color:var(--muted); margin-top:4px; }}
.idx-rule {{ width:100%; height:1px; background:var(--hairline); margin:12px 0; }}
img.overview {{ width:100%; }}

/* street index: 4 columns, grouped by name */
.sidx-cols {{ column-count:4; column-gap:12px; column-rule:1px solid var(--column-rule); }}
.sidx-grp {{ font-family:"Archivo Black"; font-size:13px; line-height:1;
            color:var(--ink-deep); margin:7px 0 3px; break-inside:avoid; break-after:avoid; }}
.sidx-entry {{ break-inside:avoid; margin-bottom:2px; line-height:1.16; }}
.sidx-name {{ font-size:7.5px; font-weight:700; color:var(--ink); }}
.sidx-seg {{ font-size:7px; }}
.sidx-sep {{ color:#BBAF98; }}
.sidx-rng {{ color:#A89F8C; white-space:nowrap; }}
.sidx-cells {{ color:var(--accent); font-weight:700; }}

/* line index: 2 columns of line-art colectivo cards */
.lidx-cols {{ column-count:2; column-gap:9px; }}
.bcard {{ position:relative; display:inline-block; width:100%;
         background:#FBF8F0; border:1px solid #D8C9A6; padding:7px 9px 6px;
         margin-bottom:9px; overflow:hidden; break-inside:avoid; }}
.bcard__inner {{ position:absolute; inset:3px; border:.8px solid #EAD9AC; pointer-events:none; }}
.bcard__top {{ position:relative; display:flex; gap:8px; align-items:center; }}
.bcard__sign {{ position:relative; flex:none; width:38px; }}
.bcard__signnum {{ position:absolute; left:0; right:0; top:1px; height:54%;
                  display:flex; align-items:center; justify-content:center;
                  font-family:"Archivo Black"; font-size:13px; line-height:1;
                  color:#FFFFFF; letter-spacing:-.5px; }}
.bcard__bus {{ flex:1; min-width:0; position:relative; }}
.bcard__busnum {{ position:absolute; left:87.5%; top:27.3%; transform:translate(-50%,-50%);
                 font-family:"Archivo Black"; font-size:5.5px; line-height:1;
                 color:#F1ECDF; letter-spacing:-.3px; white-space:nowrap; }}
.bcard__route {{ position:relative; display:flex; align-items:center; gap:5px;
                margin-top:5px; font-size:8px; font-weight:600; color:#5A554A;
                letter-spacing:.1px; }}
.bcard__a {{ flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis;
            white-space:nowrap; text-align:right; }}
.bcard__b {{ flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.bcard__arrow {{ flex:none; font-weight:800; }}
"""


def _render(body: str, out_name: str, page_rule: str):
    doc = (f"<html><head><meta charset='utf-8'><style>{page_rule}{DESIGN_CSS}"
           f"</style></head><body>{body}</body></html>")
    out = CFG.output_dir / out_name
    HTML(string=doc).write_pdf(out)
    print(f"[frontmatter] {out.name}")
    return out


PAGE_FIXED = "@page { size: 460px 720px; margin: 0; }"
PAGE_FLOW = "@page { size: 460px 720px; margin: 30px 28px 22px; background: " + TOK["paper"] + "; }"
PAGE_FLOW_LINES = "@page { size: 460px 720px; margin: 26px 22px 20px; background: #F2EEE4; }"


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
# cover (light porteña) + cómo usar
# --------------------------------------------------------------------------
def _sol_de_mayo() -> str:
    return """<svg viewBox="0 0 80 80" style="position:absolute; top:18px; right:22px; width:96px; height:96px; opacity:.85; pointer-events:none;">
      <g fill="#E6A92C"><g>
        <polygon points="40,4 43,18 37,18"></polygon><polygon points="76,40 62,43 62,37"></polygon>
        <polygon points="40,76 37,62 43,62"></polygon><polygon points="4,40 18,37 18,43"></polygon>
        <polygon points="65,15 55,24 51,20"></polygon><polygon points="65,65 56,56 60,52"></polygon>
        <polygon points="15,65 24,55 28,59"></polygon><polygon points="15,15 25,24 21,28"></polygon>
      </g><circle cx="40" cy="40" r="17"></circle></g>
      <circle cx="40" cy="40" r="17" fill="none" stroke="#C98A1E" stroke-width="1.2"></circle>
    </svg>"""


def _fileteado() -> str:
    return """<div style="position:relative; margin-top:16px; display:flex; justify-content:center;">
      <svg width="240" height="24" viewBox="0 0 240 24" fill="none">
        <g stroke="#3C82A8" stroke-width="2" stroke-linecap="round">
          <path d="M120,12 C102,12 98,3 86,5 C74,7 80,19 69,19 C60,19 60,9 50,10"></path>
          <path d="M120,12 C138,12 142,3 154,5 C166,7 160,19 171,19 C180,19 180,9 190,10"></path>
        </g>
        <g stroke="#B11E2A" stroke-width="2" stroke-linecap="round">
          <path d="M120,12 C110,12 106,7 98,8"></path><path d="M120,12 C130,12 134,7 142,8"></path>
        </g>
        <circle cx="120" cy="12" r="3.6" fill="#E0A82E"></circle>
        <circle cx="48" cy="10" r="2.4" fill="#B11E2A"></circle>
        <circle cx="192" cy="10" r="2.4" fill="#B11E2A"></circle>
      </svg></div>"""


def _skyline() -> str:
    return """<div style="position:relative; margin-top:auto;">
      <svg viewBox="0 0 392 116" style="width:100%; height:auto; display:block;">
        <g fill="#2A2620">
          <rect x="0" y="70" width="44" height="46"></rect><rect x="350" y="58" width="42" height="58"></rect>
          <rect x="300" y="74" width="40" height="42"></rect><rect x="6" y="66" width="26" height="50"></rect>
          <rect x="34" y="50" width="18" height="66"></rect><rect x="54" y="58" width="40" height="58"></rect>
          <path d="M54,58 a20,20 0 0 1 40,0 Z"></path><rect x="71" y="30" width="6" height="12"></rect>
          <rect x="73" y="22" width="2" height="9"></rect><rect x="100" y="72" width="16" height="44"></rect>
          <ellipse cx="140" cy="80" rx="22" ry="13"></ellipse><rect x="119" y="80" width="42" height="36"></rect>
          <rect x="168" y="60" width="16" height="56"></rect>
          <polygon points="222,116 226,30 230,22 234,30 238,116"></polygon>
          <rect x="250" y="66" width="18" height="50"></rect><rect x="282" y="48" width="26" height="68"></rect>
          <polygon points="282,48 295,32 308,48"></polygon><rect x="320" y="40" width="30" height="76"></rect>
          <rect x="326" y="30" width="18" height="12"></rect><rect x="331" y="22" width="8" height="9"></rect>
        </g>
        <g fill="#E6A92C">
          <rect x="12" y="72" width="2.4" height="2.4"></rect><rect x="18" y="72" width="2.4" height="2.4"></rect>
          <rect x="12" y="80" width="2.4" height="2.4"></rect><rect x="18" y="80" width="2.4" height="2.4"></rect>
          <rect x="39" y="58" width="2.4" height="2.4"></rect><rect x="44" y="58" width="2.4" height="2.4"></rect>
          <rect x="289" y="58" width="2.4" height="2.4"></rect><rect x="296" y="58" width="2.4" height="2.4"></rect>
          <rect x="328" y="50" width="2.4" height="2.4"></rect><rect x="335" y="50" width="2.4" height="2.4"></rect>
        </g>
        <line x1="0" y1="115" x2="392" y2="115" stroke="#9FB0A8" stroke-width="2"></line>
        <g transform="translate(120,101)">
          <rect x="0" y="0" width="34" height="11" rx="2.5" fill="#ED5B2A"></rect>
          <rect x="4" y="2.4" width="20" height="4" rx="1" fill="#1B1610" opacity=".4"></rect>
          <circle cx="9" cy="12" r="2.6" fill="#2A2620"></circle><circle cx="27" cy="12" r="2.6" fill="#2A2620"></circle>
        </g>
        <g transform="translate(244,99)">
          <rect x="0" y="2" width="44" height="11" rx="2" fill="#00925A"></rect>
          <rect x="3" y="4.2" width="38" height="4" rx="1" fill="#04331F" opacity=".4"></rect>
          <rect x="20" y="-2" width="3" height="4" fill="#00925A"></rect>
          <circle cx="10" cy="14" r="2.6" fill="#2A2620"></circle><circle cx="34" cy="14" r="2.6" fill="#2A2620"></circle>
        </g>
      </svg></div>"""


def _n_colectivos() -> int:
    data = json.loads((CFG.output_dir / "line_to_cells.json").read_text(encoding="utf-8"))
    return sum(1 for l in data["lines"] if l["mode"] == "colectivo")


def cover():
    title_html = "<br>".join(escape(w) for w in CFG.title.split())
    chips = "".join(
        f"<div style=\"width:26px; height:26px; border-radius:6px; display:flex;"
        f" align-items:center; justify-content:center; font-family:'Archivo Black';"
        f" font-size:13px; color:{'#1C1A15' if k == 'H' else '#fff'};"
        f" background:{SUBTE_HEX[k]};\">{k}</div>"
        for k in ("A", "B", "C", "D", "E", "H"))
    pills = "".join(
        f"<div style=\"display:flex; align-items:center; gap:5px; padding:3px 8px 3px 5px;"
        f" border-radius:20px; background:#E7DCC2;\">"
        f"<span style=\"width:9px; height:9px; border-radius:50%; background:{c};\"></span>"
        f"<span style=\"font-size:9.5px; font-weight:600; color:#4A4434;\">{escape(name)}</span></div>"
        for name, c in TREN)
    n_col = _n_colectivos()
    counts = f"{n_col} colectivos · 6 subtes · 7 trenes"

    cover_html = f"""
    <div class='page' style="background:#EFE7D3; color:#1C1A15; overflow:hidden;
         display:flex; flex-direction:column; padding:32px 34px 26px;">
      <div style="position:absolute; top:0; left:0; right:0; height:340px;
           background:linear-gradient(#C5E0EC 0%, #D9E8E4 55%, #EFE7D3 100%); pointer-events:none;"></div>
      {_sol_de_mayo()}
      <div style="position:absolute; inset:0; pointer-events:none;
           background-image:repeating-linear-gradient(90deg, rgba(28,26,21,.05) 0 1px, transparent 1px 20%),
           repeating-linear-gradient(0deg, rgba(28,26,21,.045) 0 1px, transparent 1px 14.285%);"></div>

      <div style="position:relative;">
        <div style="font-size:11px; font-weight:700; letter-spacing:2.5px; color:#B11E2A;">
          {escape(CFG.edition.upper())}</div>
      </div>

      <div style="position:relative; margin-top:24px;">
        <div style="font-size:13px; font-weight:600; letter-spacing:.5px; color:#3C6B81; margin-bottom:12px;">
          Colectivos · Subte · Trenes · Buenos Aires</div>
        <div style="font-family:'Archivo Black'; font-size:74px; line-height:.84;
             letter-spacing:-2.5px; color:#1C1A15;">{title_html}</div>
        <div style="display:flex; gap:6px; margin:18px 0 16px;">
          <div style="width:46px; height:5px; background:#4E9CC2;"></div>
          <div style="width:18px; height:5px; background:#ED5B2A;"></div>
          <div style="width:10px; height:5px; background:#E0A82E;"></div>
        </div>
        <div style="font-size:14.5px; line-height:1.45; color:#5A554A; max-width:300px;">
          El mapa de bolsillo de la ciudad. Buscás la calle, leés la celda, encontrás la línea.</div>
      </div>

      {_fileteado()}
      {_skyline()}

      <div style="position:relative; margin-top:14px; display:flex; flex-direction:column; gap:11px;">
        <div style="display:flex; align-items:center; gap:10px;">
          <div style="font-size:10px; font-weight:700; letter-spacing:1.5px; color:#8A8273; width:42px;">SUBTE</div>
          <div style="display:flex; gap:6px;">{chips}</div>
        </div>
        <div style="display:flex; align-items:center; gap:10px;">
          <div style="font-size:10px; font-weight:700; letter-spacing:1.5px; color:#8A8273; width:42px;">TREN</div>
          <div style="display:flex; flex-wrap:wrap; gap:5px;">{pills}</div>
        </div>
      </div>

      <div style="position:relative; margin-top:15px; border-top:1px solid #D6CCB4; padding-top:13px;
           display:flex; justify-content:space-between; align-items:flex-end; gap:16px;">
        <div style="font-size:9.5px; line-height:1.6; color:#8A8273;">
          <div>Recorridos AMBA · Min. Transporte (CC-BY 4.0)</div>
          <div>Callejero, subte y manzanas · GCBA</div>
          <div>Trenes Argentinos · Puntos de interés © OSM</div>
        </div>
        <div style="font-size:9.5px; color:#6E6655; text-align:right; line-height:1.5; white-space:nowrap;">
          {counts}<br>Escala 1:20 000 · EPSG:9498</div>
      </div>
    </div>"""

    return _render(cover_html + _como_usar_html(), "cover.pdf", PAGE_FIXED)


def _mini_grid() -> str:
    """5x7 grid with C4 filled and A-E / 1-7 gutters (flex + table; WeasyPrint
    has no CSS grid)."""
    top = "".join(
        f"<span style=\"width:22px; text-align:center; font-size:9px; font-weight:700;"
        f" color:{'#ED5B2A' if c == 'C' else '#8C877C'};\">{c}</span>"
        for c in "ABCDE")
    left = "".join(
        f"<span style=\"height:22px; line-height:22px; width:12px; text-align:right;"
        f" font-size:9px; font-weight:700; color:{'#ED5B2A' if n == 4 else '#8C877C'};\">{n}</span>"
        for n in range(1, 8))
    rows = "".join(
        "<tr>" + "".join(
            "<td style='width:22px; height:22px; border:1px solid #C7BEA9; padding:0;"
            + ("background:#ED5B2A; opacity:.85;'></td>" if (r == 3 and c == 2) else "'></td>")
            for c in range(5)) + "</tr>"
        for r in range(7))
    return f"""<div style="flex:none;">
      <div style="display:flex; padding-left:16px; margin-bottom:4px;">{top}</div>
      <div style="display:flex;">
        <div style="display:flex; flex-direction:column; padding-right:4px;">{left}</div>
        <table style="border-collapse:collapse; border:1px solid #C7BEA9;">{rows}</table>
      </div></div>"""


def _como_usar_html() -> str:
    steps = [
        ("1", "Buscá la calle",
         "Encontrá tu calle en el índice y anotá la referencia. Por ejemplo "
         "<b>12-C4</b> — página 12, celda C4."),
        ("2", "Ubicá la celda en el mapa",
         "Andá a la página de mapa 12 y ubicá la celda C4: las letras (A–E) van "
         "arriba y los números (1–7) al costado."),
        ("3", "Leé las líneas al lado",
         "En la página de al lado, la grilla de líneas usa la misma cuadrícula. "
         "Los números son colectivos; la letra de color es el subte."),
    ]
    steps_html = "".join(
        f"""<div style="display:flex; gap:16px; align-items:flex-start;">
          <div style="flex:none; width:30px; height:30px; background:#17150F; color:#F1ECDF;
               font-family:'Archivo Black'; font-size:15px; display:flex; align-items:center;
               justify-content:center;">{n}</div>
          <div style="flex:1;">
            <div style="font-size:16px; font-weight:700; color:#1C1A15; margin-bottom:4px;">{t}</div>
            <div style="font-size:13.5px; line-height:1.5; color:#5A554A;">{d}</div></div></div>"""
        for n, t, d in steps)
    return f"""
    <div class='page' style="background:#F5F2EA; display:flex; flex-direction:column; padding:40px 38px 30px;">
      <div style="font-size:12px; font-weight:700; letter-spacing:1.5px; color:#ED5B2A; margin-bottom:6px;">
        {escape(CFG.title.upper())}</div>
      <div style="font-family:'Archivo Black'; font-size:40px; letter-spacing:-1.5px; line-height:1; color:#1C1A15;">
        Cómo usar</div>
      <div style="width:100%; height:1px; background:#DAD3C4; margin:24px 0 26px;"></div>
      <div style="display:flex; flex-direction:column; gap:24px;">{steps_html}</div>
      <div style="margin-top:auto; background:#EDE7D8; border:1px solid #DED7C6; padding:20px;
           display:flex; gap:22px; align-items:center;">
        {_mini_grid()}
        <div>
          <div style="font-size:12px; font-weight:700; color:#1C1A15; margin-bottom:4px;">
            Referencia <span style="color:#ED5B2A;">12-C4</span></div>
          <div style="font-size:12.5px; line-height:1.45; color:#5A554A;">
            Página 12, columna C, fila 4. La misma celda existe en el mapa y en la grilla de líneas.</div>
        </div>
      </div>
    </div>"""


def overview():
    uri = make_overview_png()
    body = f"""
    <div class='idx-head'><div><div class='kicker'>Guía Abierta</div>
      <div class='idx-sub'>Mapa índice — número de página por zona</div></div></div>
    <div class='idx-rule'></div>
    <img class='overview' src='{uri}'>"""
    return _render(body, "overview.pdf", PAGE_FLOW)


# --------------------------------------------------------------------------
# street index: 4 columns, grouped by name into segments
# --------------------------------------------------------------------------
def _first_letter(name: str) -> str:
    for ch in name:
        if ch.isalpha():
            return "Ñ" if ch.lower() == "ñ" else unicodedata.normalize("NFD", ch)[0].upper()
    return "#"


def _trim_name(name: str) -> str:
    name = name.replace(" (NO OFICIAL)", "").strip()
    return name if len(name) <= 26 else name[:25].rstrip() + "…"


def _group_streets(entries: list) -> list:
    groups: list = []
    for e in entries:
        seg = {"range": e.get("range"), "refs": e["refs"]}
        if groups and groups[-1]["name"] == e["name"]:
            groups[-1]["segs"].append(seg)
        else:
            groups.append({"name": e["name"], "segs": [seg]})
    return groups


def _seg_html(seg: dict) -> str:
    rng = (f"<span class='sidx-rng'>{escape(seg['range'])}{NBSP}</span>"
           if seg.get("range") else "")
    cells = " ".join(f"<span class='nw'>{escape(r)}</span>" for r in seg["refs"])
    return (f"<span class='sidx-seg'><span class='sidx-sep'> ·{NBSP}</span>"
            f"{rng}<span class='sidx-cells'>{cells}</span></span>")


def street_index_pdf():
    data = json.loads((CFG.output_dir / "street_index.json").read_text(encoding="utf-8"))
    parts, cur = [], None
    for g in _group_streets(data["entries"]):
        letter = _first_letter(g["name"])
        if letter != cur:
            cur = letter
            parts.append(f"<div class='sidx-grp'>{escape(letter)}</div>")
        segs = "".join(_seg_html(s) for s in g["segs"])
        parts.append(f"<div class='sidx-entry'><span class='sidx-name'>"
                     f"{escape(_trim_name(g['name']))}</span>{segs}</div>")
    head = ("<div class='idx-head'><div>"
            "<div class='kicker'>Índice de calles</div>"
            "<div class='idx-sub'>calle · rango · página-celda</div></div></div>"
            "<div class='idx-rule'></div>")
    body = head + f"<div class='sidx-cols'>{''.join(parts)}</div>"
    return _render(body, "street_index.pdf", PAGE_FLOW)


# --------------------------------------------------------------------------
# line index: line-art colectivo cards (pentagon route sign + bus + recorrido)
# --------------------------------------------------------------------------
def _line_key(line):
    return (0, int(line)) if str(line).isdigit() else (1, str(line))


def _livery(line) -> tuple:
    s = str(line)
    if s in LIVERY:
        return LIVERY[s]
    seed = int(s) if s.isdigit() else zlib.crc32(s.encode())
    h = ((seed * 137) % 360) / 360.0
    rr, rg, rb = colorsys.hls_to_rgb(h, 0.34, 0.55)            # dark roof
    sr, sg, sb = colorsys.hls_to_rgb((h + 0.5) % 1.0, 0.52, 0.72)  # warm stripe
    roof = f"#{int(rr * 255):02x}{int(rg * 255):02x}{int(rb * 255):02x}"
    stripe = f"#{int(sr * 255):02x}{int(sg * 255):02x}{int(sb * 255):02x}"
    return roof, stripe


def _cabeceras(ln) -> tuple:
    streets = ln.get("streets") or []
    if len(streets) >= 2:
        return streets[0], streets[-1]
    if len(streets) == 1:
        return streets[0], streets[0]
    cells = sorted({c for refs in ln["directions"].values() for c in refs})
    return (cells[0] if cells else "", cells[-1] if cells else "")


def _bus_card(ln) -> str:
    num = escape(str(ln["line"]))
    roof, stripe = _livery(ln["line"])
    a, b = _cabeceras(ln)
    a, b = escape(a.title()), escape(b.title())
    sign = f"""<div class="bcard__sign">
      <svg viewBox="0 0 44 52" style="width:100%; height:auto; display:block;">
        <path d="M3,5 Q3,2 6,2 L38,2 Q41,2 41,5 L41,30 Q41,32.5 39.3,34 L24,48.5 Q22,50.3 20,48.5 L4.7,34 Q3,32.5 3,30 Z" fill="{roof}" stroke="#1C1A15" stroke-width="1.6"></path>
        <path d="M7,6.5 Q7,5.5 8,5.5 L36,5.5 Q37,5.5 37,6.5 L37,29.5 Q37,30.5 36.4,31 L22.5,44 Q22,44.5 21.5,44 L7.6,31 Q7,30.5 7,29.5 Z" fill="none" stroke="#FFFFFF" stroke-width="1" opacity=".9"></path>
      </svg>
      <div class="bcard__signnum">{num}</div></div>"""
    bus = f"""<div class="bcard__bus">
      <svg viewBox="0 0 232 86" style="width:100%; height:auto; display:block;">
        <path d="M11,63 L11,25 Q11,17 19,17 L207,17 Q214,17.5 218,24 L223,41 Q224,45 224,50 L224,61 Q224,63 221,63 Z" fill="#FCFAF3" stroke="#1C1A15" stroke-width="1.7" stroke-linejoin="round"></path>
        <rect x="11" y="45" width="213" height="6.6" fill="{stripe}"></rect>
        <rect x="11" y="59.5" width="210" height="3.5" fill="{stripe}"></rect>
        <g fill="{GLASS}" stroke="#1C1A15" stroke-width=".9">
          <rect x="22" y="29" width="23" height="14" rx="1.6"></rect>
          <rect x="49" y="29" width="23" height="14" rx="1.6"></rect>
          <rect x="76" y="29" width="23" height="14" rx="1.6"></rect>
          <rect x="103" y="29" width="23" height="14" rx="1.6"></rect>
          <rect x="130" y="29" width="23" height="14" rx="1.6"></rect>
          <rect x="157" y="29" width="23" height="14" rx="1.6"></rect>
          <path d="M204,29 L218,43 L186,43 L186,29 Z"></path></g>
        <g fill="none" stroke="#1C1A15" stroke-width=".8" opacity=".55">
          <rect x="22" y="20.5" width="158" height="6" rx="1"></rect>
          <line x1="48.5" y1="20.5" x2="48.5" y2="26.5"></line>
          <line x1="75" y1="20.5" x2="75" y2="26.5"></line>
          <line x1="101.5" y1="20.5" x2="101.5" y2="26.5"></line>
          <line x1="128" y1="20.5" x2="128" y2="26.5"></line>
          <line x1="154.5" y1="20.5" x2="154.5" y2="26.5"></line></g>
        <rect x="186" y="19.5" width="34" height="8" rx="1.4" fill="#17150F"></rect>
        <g fill="none" stroke="#1C1A15" stroke-width="1">
          <line x1="184" y1="45" x2="184" y2="63"></line>
          <rect x="186" y="45.5" width="16" height="17.5"></rect>
          <line x1="194" y1="45.5" x2="194" y2="63"></line>
          <line x1="70" y1="45" x2="70" y2="63"></line>
          <line x1="74" y1="45" x2="74" y2="63"></line></g>
        <path d="M11,63 L11,25 Q11,17 19,17 L207,17 Q214,17.5 218,24 L223,41 Q224,45 224,50 L224,61 Q224,63 221,63" fill="none" stroke="#1C1A15" stroke-width="1.7" stroke-linejoin="round"></path>
        <circle cx="222" cy="55" r="2.4" fill="#FCE08A" stroke="#1C1A15" stroke-width=".6"></circle>
        <g stroke="#1C1A15" stroke-width="1.5">
          <circle cx="58" cy="63" r="12.5" fill="#FCFAF3"></circle>
          <circle cx="58" cy="63" r="5" fill="#CFC8B8"></circle>
          <circle cx="186" cy="63" r="12.5" fill="#FCFAF3"></circle>
          <circle cx="186" cy="63" r="5" fill="#CFC8B8"></circle></g>
      </svg>
      <div class="bcard__busnum">{num}</div></div>"""
    return f"""<div class="bcard"><div class="bcard__inner"></div>
      <div class="bcard__top">{sign}{bus}</div>
      <div class="bcard__route">
        <span class="bcard__a">{a}</span>
        <span class="bcard__arrow" style="color:{roof};">→</span>
        <span class="bcard__b">{b}</span></div></div>"""


def line_index_pdf():
    data = json.loads((CFG.output_dir / "line_to_cells.json").read_text(encoding="utf-8"))
    colect = sorted((l for l in data["lines"] if l["mode"] == "colectivo"),
                    key=lambda l: _line_key(l["line"]))
    cards = "".join(_bus_card(l) for l in colect)
    head = f"""
    <div class='idx-head'>
      <div><div class='kicker'>Líneas de colectivo</div>
        <div class='idx-sub'>recorrido · cabecera a cabecera</div></div>
      <div style="text-align:right;">
        <div style="font-family:'Archivo Black'; font-size:30px; line-height:.8; color:#17150F;">{len(colect)}</div>
        <div style="font-size:9px; color:#8C877C; margin-top:2px;">líneas en la guía</div></div>
    </div>
    <div style="display:flex; align-items:center; gap:8px; margin:14px 0;">
      <div style="height:1px; flex:1; background:#D8C9A6;"></div>
      <svg width="46" height="10" viewBox="0 0 46 10"><path d="M2,8 C 8,2 16,2 23,6 C 30,2 38,2 44,8" fill="none" stroke="#C99B33" stroke-width="1.3"></path><circle cx="23" cy="6" r="1.6" fill="#C99B33"></circle></svg>
      <div style="height:1px; flex:1; background:#D8C9A6;"></div>
    </div>"""
    body = head + f"<div class='lidx-cols'>{cards}</div>"
    return _render(body, "line_index.pdf", PAGE_FLOW_LINES)


def build_frontmatter() -> list:
    return [cover(), overview(), street_index_pdf(), line_index_pdf()]


if __name__ == "__main__":
    build_frontmatter()
