"""Guía Abierta — matplotlib style module (map pages + line-grid pages).

Ported from design_handoff_guia_estilo/mpl_style.py. Geometry stays ours (real
reprojected geo at 1:20000); this only carries the palette, line weights, font
sizes and z-order from the design reference.
"""
from __future__ import annotations

from matplotlib import rcParams

import fonts  # registers the bundled Public Sans / Archivo Black

GUIA = {
    # paper / blocks
    "paper":         "#F5F2EA",   # page background
    "map_base":      "#F3ECDD",   # street/void base on the map
    "manzana_fill":  "#E9DDC2",   # city blocks (GCBA manzanas)
    "manzana_edge":  "none",

    # avenidas (highlighted streets), drawn as a casing
    "avenida_fill":  "#F6EAC4",
    "avenida_edge":  "#E0CE96",
    "avenida_lw":    2.2,
    "avenida_casing_lw": 3.4,

    # parks / landmarks
    "park_face":     (0.0, 0.573, 0.353, 0.20),
    "park_edge":     (0.0, 0.573, 0.353, 0.45),
    "park_label":    "#0A6B45",

    # subte
    "subte_line_lw": 1.6,
    "station_face":  "#FFFFFF",
    "station_ring":  "#1C1A15",
    "station_ring_lw": 1.1,
    "station_size":  3.0,

    # grid / frame
    "fishnet":       (0.110, 0.102, 0.082, 0.20),
    "fishnet_lw":    0.6,
    "frame":         "#1C1A15",
    "frame_lw":      1.5,
    "cell_sep":      "#C9C0AD",
    "cell_sep_lw":   1.0,

    # text / accent
    "ink":           "#1C1A15",
    "accent":        "#ED5B2A",
    "muted":         "#8C877C",
    "street_label":  "#6E6552",
    "avenida_label": "#4A4636",
    "cell_text":     "#2A271F",

    # type sizes (pt)
    "fs_gutter":     8.5,
    "fs_street":     3.7,
    "fs_avenida":    4.8,
    "fs_station":    4.2,
    "fs_cell":       8,
    "fs_folio":      11,

    # z-order (back -> front)
    "z": {
        "manzanas": 1, "avenidas": 2, "park": 3, "fishnet": 4,
        "subte": 5, "stations": 6, "labels": 7, "frame": 8,
    },
}

SUBTE = {
    "A": "#34B6E4", "B": "#E2231A", "C": "#163F8C",
    "D": "#00925A", "E": "#6C3A93", "H": "#F4C500",
    "PM-C": "#00925A", "PM-S": "#00925A",
}
SUBTE_DARK_TEXT = {"H"}


def apply_rcparams() -> None:
    fonts.register_matplotlib()
    rcParams["font.family"] = fonts.BODY
    rcParams["pdf.fonttype"] = 42       # embed TrueType (selectable text)
    rcParams["text.color"] = GUIA["ink"]
    rcParams["savefig.facecolor"] = GUIA["paper"]
