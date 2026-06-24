"""Bundled fonts, registered for both renderers.

- Public Sans (regular + bold): body, map labels, indices, line grids.
- Archivo Black: cover display title.

Both are SIL OFL (see assets/fonts/OFL-*.txt). Shipping them keeps output
identical across machines and avoids depending on system fonts.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
from matplotlib import font_manager

FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
BODY = "Public Sans"
DISPLAY = "Archivo Black"

# file -> (css family, weight)
_FILES = {
    "PublicSans-Regular.ttf": (BODY, "normal"),
    "PublicSans-Bold.ttf": (BODY, "bold"),
    "ArchivoBlack-Regular.ttf": (DISPLAY, "normal"),
}


def register_matplotlib() -> None:
    for fn in _FILES:
        p = FONT_DIR / fn
        if p.exists():
            font_manager.fontManager.addfont(str(p))
    if (FONT_DIR / "PublicSans-Regular.ttf").exists():
        matplotlib.rcParams["font.family"] = BODY


def css_font_face() -> str:
    """@font-face block for WeasyPrint, pointing at the bundled TTFs."""
    out = []
    for fn, (fam, weight) in _FILES.items():
        p = FONT_DIR / fn
        if p.exists():
            out.append(
                f"@font-face {{ font-family:'{fam}'; font-weight:{weight}; "
                f"src:url('{p.as_uri()}'); }}"
            )
    return "\n".join(out)


# register for matplotlib as soon as this module is imported
register_matplotlib()
