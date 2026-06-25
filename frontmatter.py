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
import zlib
from html import escape

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from weasyprint import HTML

import fonts  # noqa: E402  registers bundled fonts for matplotlib
from config import CFG
from grid import load_boundary, load_grid
from names import abbreviate

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

/* street index: continuous dense flow, 4 columns, bullet-separated */
.sidx-cols {{ column-count:4; column-gap:11px; column-rule:1px solid var(--column-rule);
             font-size:7px; line-height:1.26; text-align:left; -weasy-hyphens:none; }}
.sidx-entry {{ break-inside:avoid; margin-bottom:1.5px; }}
.sidx-name {{ font-weight:700; color:var(--ink); }}
.sidx-alt {{ padding-left:7px; }}
.sidx-rng {{ color:#A89F8C; }}
.sidx-cells {{ color:var(--accent); }}
.sidx-pg {{ color:var(--accent); font-weight:700; }}

/* line index: one column; "cartel de parada" sign floated so the route text
   wraps around and under it (no white space beside short rows). */
/* no break-inside:avoid -> a long entry may split across pages and fill the
   bottom of each page instead of leaving it blank. */
.lrow {{ display:flow-root; padding:2px 1px; border-bottom:1px solid #E2D8C2; }}
.lrow__sign {{ position:relative; float:left; width:36px; margin:1px 7px 0 0; }}
.lrow__signnum {{ position:absolute; left:0; right:0; top:0; height:78%;
                 display:flex; align-items:center; justify-content:center;
                 font-family:"Archivo Black"; line-height:1; letter-spacing:-.5px; }}
.lrow__route {{ font-size:7.5px; line-height:1.24; color:#3A362C; }}
.lrow__ramal {{ font-weight:700; font-size:7px; text-transform:uppercase;
               letter-spacing:.4px; margin:2.5px 0 .5px; }}
.lrow__line + .lrow__line {{ margin-top:1.5px; }}
.lrow__dir {{ color:#A8895A; font-weight:700; font-size:6.3px; text-transform:uppercase;
             letter-spacing:.3px; }}
"""


def _render(body: str, out_name: str, page_rule: str):
    doc = (f"<html><head><meta charset='utf-8'><style>{page_rule}{DESIGN_CSS}"
           f"</style></head><body>{body}</body></html>")
    out = CFG.output_dir / out_name
    HTML(string=doc).write_pdf(out)
    print(f"[frontmatter] {out.name}")
    return out


_FOLIO = ("@bottom-right { content: counter(page, decimal-leading-zero); "
          "font-family: 'Archivo Black'; font-size: 10px; color: #17150F; }")
PAGE_FIXED = "@page { size: 460px 720px; margin: 0; }"
PAGE_FLOW = ("@page { size: 460px 720px; margin: 30px 28px 24px; background: "
             + TOK["paper"] + "; " + _FOLIO + " }")
PAGE_FLOW_LINES = ("@page { size: 460px 720px; margin: 26px 22px 22px; background: #F2EEE4; "
                   + _FOLIO + " }")


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


def _cell_key(cell: str):
    return (cell[0], int(cell[1:]))


def _page_groups(refs: list) -> str:
    """page printed once, then its cells; central dot separates the groups."""
    by_page: dict = {}
    for ref in refs:
        page, cell = ref.split("-")
        by_page.setdefault(page, []).append(cell)
    groups = []
    for page, cells in by_page.items():
        cs = ", ".join(sorted(set(cells), key=_cell_key))
        groups.append(f"<span class='sidx-pg'>{escape(page)}</span> {cs}")
    return f"<span class='sidx-cells'>{' · '.join(groups)}</span>"


def _entry_html(g: dict) -> str:
    name = f"<span class='sidx-name'>{escape(_trim_name(g['name']))}</span>"
    inline, alt = [], []
    for s in g["segs"]:
        if s.get("range"):
            alt.append(f"<div class='sidx-alt'><span class='sidx-rng'>"
                       f"{escape(s['range'])}</span> {_page_groups(s['refs'])}</div>")
        else:
            inline.append(_page_groups(s["refs"]))
    inline_html = (" " + " · ".join(inline)) if inline else ""
    return f"<div class='sidx-entry'>{name}{inline_html}{''.join(alt)}</div>"


def street_index_pdf():
    data = json.loads((CFG.output_dir / "street_index.json").read_text(encoding="utf-8"))
    items = "".join(_entry_html(g) for g in _group_streets(data["entries"]))
    head = ("<div class='idx-head'><div>"
            "<div class='kicker'>Índice de calles</div>"
            "<div class='idx-sub'>calle · altura · página, celdas</div></div></div>"
            "<div class='idx-rule'></div>")
    body = head + f"<div class='sidx-cols'>{items}</div>"
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


def _clip_route(streets: list, cap: int = 6) -> str:
    """Abbreviate, keep both ends (origin + destination matter for the ramal),
    and trim the middle with an ellipsis so routes stay short."""
    if len(streets) > cap:
        streets = streets[:cap - 1] + ["…", streets[-1]]
    parts = [s if s == "…" else abbreviate(s).title() for s in streets]
    return " · ".join(escape(p) for p in parts)


def _route_rows(ln) -> str:
    """Each ramal on its own (header + its ida / vuelta routes). Keys are
    "ramal::dir" (or plain "dir"). The ramal header shows only when a line has
    more than one ramal."""
    routes = ln.get("routes") or {}
    by_ramal: dict = {}
    for key, streets in routes.items():
        ramal, d = key.split("::", 1) if "::" in key else ("", key)
        by_ramal.setdefault(ramal, {})[d] = streets
    multi = len(by_ramal) > 1
    color = _livery(ln["line"])[0]
    rows = []
    for ramal in sorted(by_ramal):
        dirs = by_ramal[ramal]
        if multi and ramal:
            rows.append(f"<div class='lrow__ramal' style='color:{color}'>"
                        f"Ramal {escape(ramal)}</div>")
        order = [k for k in ("ida", "vuelta") if k in dirs]
        order += [k for k in dirs if k not in ("ida", "vuelta")]
        for d in order:
            streets = dirs.get(d) or []
            if not streets:
                continue
            label = (f"<span class='lrow__dir'>{escape(d)}</span> "
                     if d in ("ida", "vuelta") else "")
            rows.append(f"<div class='lrow__line'>{label}{_clip_route(streets)}</div>")
    if not rows:
        streets = ln.get("streets") or []
        if streets:
            rows.append(f"<div class='lrow__line'>{_clip_route(streets)}</div>")
    return "".join(rows)


def _bus_row(ln) -> str:
    s = str(ln["line"])
    num = escape(str(int(s)) if s.isdigit() else s)
    c = _livery(ln["line"])[0]
    fs = 11 if len(num) <= 3 else 8.5
    # "cartel de parada": rounded sign on a short post, number in the line color
    sign = f"""<div class="lrow__sign">
      <svg viewBox="0 0 56 40" style="width:100%; height:auto; display:block;">
        <rect x="26.3" y="29" width="3.4" height="10" fill="{c}"></rect>
        <rect x="2" y="2" width="52" height="29" rx="5" fill="#FCFAF3" stroke="{c}" stroke-width="2.4"></rect>
        <rect x="5" y="5" width="46" height="23" rx="3" fill="none" stroke="{c}" stroke-width=".7" opacity=".45"></rect>
      </svg>
      <div class="lrow__signnum" style="color:{c}; font-size:{fs}px;">{num}</div></div>"""
    return f'<div class="lrow">{sign}<div class="lrow__route">{_route_rows(ln)}</div></div>'


def line_index_pdf():
    data = json.loads((CFG.output_dir / "line_to_cells.json").read_text(encoding="utf-8"))
    colect = sorted((l for l in data["lines"] if l["mode"] == "colectivo"),
                    key=lambda l: _line_key(l["line"]))
    rows = "".join(_bus_row(l) for l in colect)
    head = f"""
    <div class='idx-head'>
      <div><div class='kicker'>Líneas de colectivo</div>
        <div class='idx-sub'>recorrido por calles</div></div>
      <div style="text-align:right;">
        <div style="font-family:'Archivo Black'; font-size:30px; line-height:.8; color:#17150F;">{len(colect)}</div>
        <div style="font-size:9px; color:#8C877C; margin-top:2px;">líneas en la guía</div></div>
    </div>
    <div style="display:flex; align-items:center; gap:8px; margin:14px 0;">
      <div style="height:1px; flex:1; background:#D8C9A6;"></div>
      <svg width="46" height="10" viewBox="0 0 46 10"><path d="M2,8 C 8,2 16,2 23,6 C 30,2 38,2 44,8" fill="none" stroke="#C99B33" stroke-width="1.3"></path><circle cx="23" cy="6" r="1.6" fill="#C99B33"></circle></svg>
      <div style="height:1px; flex:1; background:#D8C9A6;"></div>
    </div>"""
    body = head + f"<div class='lidx'>{rows}</div>"
    return _render(body, "line_index.pdf", PAGE_FLOW_LINES)


def build_frontmatter() -> list:
    return [cover(), overview(), street_index_pdf(), line_index_pdf()]


if __name__ == "__main__":
    build_frontmatter()
