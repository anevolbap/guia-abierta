"""
Guía Abierta — matplotlib style module (map pages + line-grid pages).

Import into render_pages.py and reference GUIA[...] when drawing. Values are the
visual spec from the HTML design reference; geometry is yours (real reprojected
geo at 1:20000). Sizes in points are suggestions for a ~105 mm wide page — tune
to your actual figure size, but keep the *ratios* and z-order.

    from mpl_style import GUIA, apply_rcparams, SUBTE
    apply_rcparams()        # sets Public Sans + Archivo Black, crisp lines
    ...
    ax.add_collection(manzanas, facecolor=GUIA["manzana_fill"], edgecolor="none",
                      zorder=GUIA["z"]["manzanas"])
"""

from matplotlib import rcParams

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
GUIA = {
    # paper / blocks
    "paper":         "#F5F2EA",   # page background (frontmatter parity)
    "map_base":      "#F3ECDD",   # street/void base on the map
    "manzana_fill":  "#E9DDC2",   # city blocks (GCBA manzanas)
    "manzana_edge":  "none",

    # avenidas (highlighted streets)
    "avenida_fill":  "#F6EAC4",
    "avenida_edge":  "#E0CE96",
    "avenida_lw":    1.6,         # casing edge weight (pt)

    # parks / landmarks
    "park_face":     (0.0, 0.573, 0.353, 0.20),   # rgba(0,146,90,.20)
    "park_edge":     (0.0, 0.573, 0.353, 0.45),
    "park_label":    "#0A6B45",

    # subte
    "subte_line_lw": 1.6,         # pt
    "station_face":  "#FFFFFF",
    "station_ring":  None,        # set per line via SUBTE[letter]
    "station_ring_lw": 2.0,       # pt
    "station_size":  4.0,         # marker radius-ish (pt); tune to scale

    # grid / frame
    "fishnet":       (0.110, 0.102, 0.082, 0.20), # rgba(28,26,21,.20)
    "fishnet_lw":    1.0,
    "frame":         "#1C1A15",
    "frame_lw":      1.5,
    "cell_sep":      "#C9C0AD",   # inner separators on the line-grid page
    "cell_sep_lw":   1.0,

    # text
    "ink":           "#1C1A15",
    "muted":         "#8C877C",   # A–E / 1–7 gutters
    "street_label":  "#6E6552",
    "cell_text":     "#2A271F",   # line numbers in cells

    # type sizes (pt @ ~105 mm page — scale to your figure)
    "fs_gutter":     9,
    "fs_street":     6.5,
    "fs_station":    6.5,
    "fs_cell":       8,
    "fs_folio":      30,          # big page number in the running head
    "fs_header":     15,

    # z-order (draw back -> front)
    "z": {
        "map_base":  0,
        "manzanas":  1,
        "avenidas":  2,
        "park":      3,
        "fishnet":   4,
        "subte":     5,
        "stations":  6,
        "labels":    7,
        "frame":     8,
    },
}

# Subte line colors (stylized — replace with official GTFS route_color if present)
SUBTE = {
    "A": "#34B6E4",
    "B": "#E2231A",
    "C": "#163F8C",
    "D": "#00925A",
    "E": "#6C3A93",
    "H": "#F4C500",
}
# Letters whose badge needs dark text for contrast:
SUBTE_DARK_TEXT = {"H"}


# ---------------------------------------------------------------------------
# rcParams: fonts + crisp vector output
# ---------------------------------------------------------------------------
def apply_rcparams():
    # Register the bundled fonts first, e.g.:
    #   from matplotlib import font_manager
    #   for f in ("PublicSans-Regular.ttf","PublicSans-SemiBold.ttf",
    #             "PublicSans-Bold.ttf","ArchivoBlack-Regular.ttf"):
    #       font_manager.fontManager.addfont(FONT_DIR / f)
    rcParams["font.family"] = "Public Sans"
    rcParams["font.weight"] = "regular"
    rcParams["pdf.fonttype"] = 42       # embed real TrueType (selectable text)
    rcParams["axes.linewidth"] = GUIA["frame_lw"]
    rcParams["text.color"] = GUIA["ink"]
    rcParams["savefig.facecolor"] = GUIA["paper"]


# ---------------------------------------------------------------------------
# Helper: draw a subte badge inside a line-grid cell (bottom-right).
# `ax` in axes-fraction coords; (x, y) is the cell's bottom-right corner.
# ---------------------------------------------------------------------------
def subte_badge(ax, x, y, letter, size=0.018):
    from matplotlib.patches import FancyBboxPatch
    color = SUBTE.get(letter, GUIA["subte_line_lw"] and "#00925A")
    txt = GUIA["ink"] if letter in SUBTE_DARK_TEXT else "#FFFFFF"
    box = FancyBboxPatch(
        (x - size, y), size, size,
        boxstyle="round,pad=0,rounding_size=0.004",
        transform=ax.transAxes, facecolor=color, edgecolor="none",
        zorder=GUIA["z"]["labels"] + 1, mutation_aspect=1,
    )
    ax.add_patch(box)
    ax.text(x - size / 2, y + size / 2, letter, transform=ax.transAxes,
            ha="center", va="center", color=txt,
            fontfamily="Archivo Black", fontsize=GUIA["fs_cell"],
            zorder=GUIA["z"]["labels"] + 2)


# Cell line-number text: tabular figures, tight leading, wrapped to cell width.
# Use ax.text(..., fontfamily="Public Sans", fontsize=GUIA["fs_cell"],
#             color=GUIA["cell_text"], linespacing=1.28, va="top", ha="left")
# Pre-wrap the comma-joined number string to the cell's pixel width yourself
# (matplotlib won't auto-wrap) using textwrap on an estimated chars-per-line.
