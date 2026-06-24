"""Merge cover -> indices -> map pages into output/guiat.pdf."""
from __future__ import annotations

from pypdf import PdfWriter

from config import CFG

FRONT_ORDER = [
    "cover.pdf", "overview.pdf", "street_index.pdf",
    # "line_index.pdf", "landmark_index.pdf",  # disabled for now
]


def assemble() -> str:
    writer = PdfWriter()
    n = 0
    for name in FRONT_ORDER:
        p = CFG.output_dir / name
        if p.exists():
            writer.append(str(p))
            n += 1
    for page_pdf in sorted(CFG.pages_dir.glob("*.pdf")):
        writer.append(str(page_pdf))
        n += 1
    out = CFG.output_dir / "guiat.pdf"
    with open(out, "wb") as f:
        writer.write(f)
    writer.close()
    print(f"[assemble] merged {n} source PDFs -> {out}")
    return str(out)


if __name__ == "__main__":
    assemble()
