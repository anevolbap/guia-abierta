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

### Train (Tren) line colors — stylized, replace with official GTFS route_color if available
`Mitre #16A085 · Sarmiento #E8552D · Roca #1F5FB0 · San Martín #C0392B · Belgrano Norte #2E9E4B · Belgrano Sur #7E3F98 · Urquiza #E8902B`
Shown on the cover as small pill chips (colored dot + name). These belong on the **WeasyPrint** surface.

### Pocket density (important)
This edition is sized to **carry comfortably**, so the street index and line index run SMALL and dense:
- Street index: **4 columns** (like the original Guía T), name **7.5px / 700**, range+cells **7px**, row gap ~2px, `line-height:1.16`. (WeasyPrint: `column-count:4`, `column-gap:12px`, `break-inside:avoid`.)
- **Group by street name — never repeat the name.** Collapse the per-address-range rows of one street into a single entry: name once, then each `{range cells}` segment. Separate segments with a faint middot `·` (`#C7BCA3`) — the "invisible bullets". Range in muted `#A89F8C`, cells in accent `#ED5B2A` bold. Keep each segment `white-space:nowrap` so it wraps as a unit, not mid-ref.
- Pre-trim long street names (drop `(NO OFICIAL)`, collapse `Av.`/`Gral.`, cap ~24 chars) to avoid ugly wraps. Pack columns full — bias to more entries at small size, not white space.

### Bus line index — line-art colectivo + inverted-pentagon route sign
Mirrors the original Guía's printed look (refs: `silueta-bondi.png`, `numero-bondi.png`). Each line is a small framed card (cream `#FBF8F0`, double border: outer `#D8C9A6`, inner gold hairline `#EAD9AC`) holding:
- an **inverted-pentagon route sign** (home-plate, point down) filled with the line's color, thin white inner keyline, ink `#1C1A15` outline, white Archivo Black numeral in the square upper part. This replaces the earlier bracketed plate.
- a **line-art side-view colectivo** copied from the real reference: long low body, ink outline `#1C1A15` (1.7px) on near-white `#FCFAF3`, TWO window rows (small clerestory vents above the main glazing), raked front windshield, glass `#BFD8E0`, front + middle doors, dark destination blind with the line number, two big **hollow** wheels (dark tire, light hub). Livery shows as a **beltline stripe at the window sill + a thin lower skirt line** (NOT a colored roof — that was the earlier mistake).
- **recorrido** below as `cabecera → cabecera`, ellipsis-clamped per end (arrow takes the line color).

Liveries (roof / stripe) — **representative, confirm per operating company before press.** Only the **60** is sourced (Micro Omnibus Norte: soft-yellow base, red stripe, night-blue roof → roof `#16306B`, stripe `#C8202A`, base `#F4D03F`). Others approximate: 15 `#15448F`/`#E2231A` · 19 `#1E7A3E`/`#F4C20D` · 29 `#B11E2A`/`#E8902B` · 107 `#E8702A`/`#15346B` · 114 `#00838F`/`#F4C20D` · 130 `#1F3A6E`/`#E8902B` · 133 `#1E7A46`/`#C8202A` · 152 `#15346B`/`#C8202A` · 160 `#7A1F2B`/`#E8B23A` · 166 `#5E3A8C`/`#F4C20D` · 168 `#0E7C7B`/`#E8902B`. Glass `#BFD8E0`. Source liveries per line from busarg.com.ar (per-company libreas) when generating for real. This is a **WeasyPrint** page — bus + plate are inline SVG, fully reproducible in HTML/CSS.

### Cover — light & porteña
The cover is **light, not dark**: warm paper `#EFE7D3` with a **celeste sky** gradient up top (`#C5E0EC → #EFE7D3`) behind the title, a **Sol de Mayo** (gold `#E6A92C`, rayed) in the top-right corner, the Archivo Black title in ink `#1C1A15`, a celeste/orange/gold rule (`#4E9CC2` / `#ED5B2A` / `#E0A82E`), and a small **fileteado porteño** flourish (symmetric scrollwork in celeste + bordó `#B11E2A` + gold). The Buenos Aires **skyline frieze** (Obelisco, Congreso & Planetario domes, Torre Monumental, Kavanagh-style tower) sits at the bottom as an ink `#2A2620` silhouette on a faint celeste ground line, with gold lit windows and a small orange colectivo + green tren on the street line. Subte chips keep their colors; tren chips become light pills (`#E7DCC2`) with colored dots + dark text. This is the **WeasyPrint** cover — all inline SVG/CSS.

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
