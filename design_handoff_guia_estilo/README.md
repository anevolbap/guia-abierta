# Handoff: Guía Abierta — estilo visual

## What this is
A complete **visual style spec** for the Guía Abierta pocket guide, derived from an HTML design
reference (`Guia Abierta.dc.html`, included in this folder). It exists so a Claude Code session can
apply a consistent look to the PDF generator **without re-deriving any colors, fonts, or sizes**.

> The HTML file is a **design reference**, not code to ship. Your pipeline generates PDFs from data
> with matplotlib + WeasyPrint; the job is to port these *values* into that pipeline.

## How to feed this to Claude Code
1. Copy this `design_handoff_guia_estilo/` folder into your repo.
2. Prompt Claude Code, e.g.:
   > Read `design_handoff_guia_estilo/README.md`. Apply the **WeasyPrint surface** spec + `frontmatter.css`
   > to `frontmatter.py` (cover, page-overview, street index, line index). Apply the **matplotlib surface**
   > spec + `mpl_style.py` to `render_pages.py` (map pages and line-grid pages). Keep the bundled fonts.
3. Iterate per surface — they're independent.

## Two styling surfaces (this is the key split)
| Surface | Your files | What to change | Asset in this folder |
|---|---|---|---|
| **WeasyPrint** (HTML/CSS → PDF) | `frontmatter.py` | CSS for cover, overviews, street index, line index | `frontmatter.css` (drop-in) |
| **matplotlib** (Agg → PDF) | `render_pages.py` | colors, line weights (pt), font sizes, z-order, marker sizes | `mpl_style.py` (style module) |

Fonts (**Public Sans** + **Archivo Black**) are already bundled and apply to both — keep them so type
stays consistent across the two surfaces.

## Fidelity
**High-fidelity** for the frontmatter (cover/indices): exact colors, type, spacing — port pixel-faithfully.
The **map page is a stylized reference only** — you draw real reprojected geo, so treat the map spec as a
*color / line-weight / z-order* guide, not geometry.

---

## Design tokens (shared)

### Color
| Token | Hex | Use |
|---|---|---|
| `paper` | `#F5F2EA` | page background |
| `panel` | `#EDE7D8` | callout / inset background |
| `panel-border` | `#DED7C6` | callout border |
| `ink` | `#1C1A15` | primary text, grid frame |
| `ink-deep` | `#17150F` | cover bg, folios, step-number chips |
| `cream` | `#F1ECDF` | text on dark |
| `muted` | `#8C877C` | labels, A–E / 1–7 gutters |
| `muted-2` | `#9A9384` | index cell suffix, footnotes |
| `body` | `#5A554A` | paragraph text |
| `accent` | `#ED5B2A` | kickers, page numbers, rule, highlight cell |
| `hairline` | `#DAD3C4` | dividers |
| `column-rule` | `#E4DDCE` | index column rule |

### Subte line colors (stylized — swap your official hexes if you have them)
`A #34B6E4 · B #E2231A · C #163F8C · D #00925A · E #6C3A93 · H #F4C500`
Badge: rounded square (radius 3px), Archivo Black letter, white text (H uses ink `#1C1A15`).

### Type
- **Archivo Black** — cover title, section folio numbers, index letter-tab, subte badges, step-number chips.
- **Public Sans** — everything else. Weights used: 400 / 500 / 600 / 700.
- Kickers/labels: 700, letter-spacing 1.5–2.5px, uppercase, in `accent` or `muted`.

### Geometry
- Page (design reference): **460 × 720 px**, ratio ≈ 0.639 → a 105 × 164 mm trim. Set this in `@page` /
  your imposition; all px below are at the 460-wide reference (scale proportionally for your real trim).
- Grid: **5 columns A–E × 7 rows 1–7**. Gutters 15px. Frame `1.5px ink`, inner cell lines `1px #C9C0AD`.

---

## WeasyPrint surface — page specs

### Cover (`.cover`)
- Background `ink-deep`; faint accent fishnet overlay (orange 1px lines, 20% / 14.285% spacing, ~8–10% alpha).
- Kicker `EDICIÓN ABIERTA` (accent, 700, ls 2.5) ↔ `v2026·06` (muted).
- Title `Guía / Abierta` Archivo Black **88px**, line-height .84, letter-spacing -3px, `cream`.
- Accent rule 60×5px under title.
- Tagline 15px `#C9C2B1`, max-width 300px.
- Subte color chips row (6 × 34px squares, radius 7, gap 7).
- Footer: 4 credit lines (9.5px `#7C766A`) ↔ `Escala 1:20 000 / EPSG:9498`.

### Cómo usar (`.como-usar`)
- Kicker `GUÍA ABIERTA` + title **Cómo usar** (Archivo Black 40, ls -1.5).
- 3 numbered steps: 30px `ink-deep` square chip (Archivo Black 15) + title (16/700) + body (13.5/1.5 `body`).
- Inset diagram (`panel` bg): mini 5×7 grid (22px cells, `#C7BEA9` lines) with **C4 filled accent**, A–E/1–7
  gutters, caption `Referencia 12-C4`.

### Índice de calles (`.indice`)
- Header kicker `ÍNDICE DE CALLES` + sub `calle · página-celda`, big letter-tab `A` (Archivo Black 54, `ink-deep`).
- Body: **`column-count: 2`**, `column-gap: 26px`, `column-rule: 1px solid #E4DDCE`. Each entry
  `break-inside: avoid`. Entry = name (11.5/600 `ink`) + refs; each ref = **page bold accent** + `-cell` muted.
- Footer note + folio (Archivo Black).

**WeasyPrint caveats**: use `columns` (done) not flex for the index; avoid relying on flex `gap` —
use margins; gradients/`@font-face`/`transform` are supported. See `frontmatter.css`.

---

## matplotlib surface — map + line-grid specs
All values live in `mpl_style.py` as a `GUIA` dict. Highlights:

### Map page
- Manzana fill `#E9DDC2` on street base `#F3ECDD` (block pitch ~12px fill / 4px street gap at reference scale).
- Avenida casing: fill `#F6EAC4`, edge `#E0CE96`.
- Park: face `rgba(0,146,90,.20)`, edge `rgba(0,146,90,.45)`, label `#0A6B45`.
- Subte line: `#00925A`, width ≈1.6pt; stations = white face + 2pt `#00925A` ring.
- Fishnet grid: `rgba(28,26,21,.20)` 1px; page frame `#1C1A15` 1.5pt.
- Street labels `#6E6552`; subte/station labels `#0A6B45`; A–E/1–7 gutters Public Sans 700 ~9pt `#8C877C`.
- **z-order**: manzanas → avenidas → park → fishnet grid → subte line → stations → labels → page frame.

### Line-grid page
- Frame `#1C1A15` 1.5pt; cell separators `#C9C0AD` 1pt.
- Cell line list: Public Sans ~8pt, color `#2A271F`, tabular figures, tight leading (~1.28), wrap inside cell.
- Subte badge bottom-right of cell: `#00925A` rounded square, Archivo Black white letter.
- Gutters identical to map page so the two pages register cell-for-cell.

## Files in this folder
- `README.md` — this spec.
- `frontmatter.css` — drop-in CSS for the WeasyPrint pages (cover / cómo-usar / índice).
- `mpl_style.py` — Python style module (`GUIA` dict + `apply_rcparams()`) for the matplotlib pages.
- `Guia Abierta.dc.html` — the HTML design reference (open in a browser to see the target).
