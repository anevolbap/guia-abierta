"""Booklet imposition: turn the sequential A5 PDF into 2-up saddle-stitch
sheets so it can be printed double-sided, folded once, and stapled.

Each output sheet side is two A5 pages side by side. The page order is the
classic outside-in saddle-stitch sequence; the page count is padded with blanks
to a multiple of 4. Print double-sided (flip on short edge), fold, staple.
"""
from __future__ import annotations

from pypdf import PageObject, PdfReader, PdfWriter, Transformation

from config import CFG


def _saddle_order(total: int) -> list[tuple[int, int]]:
    """(left, right) 0-based page indices for each sheet side, outside-in."""
    order = []
    lo, hi = 0, total - 1
    while lo < hi:
        order.append((hi, lo))          # front of the sheet
        order.append((lo + 1, hi - 1))  # back of the sheet
        lo += 2
        hi -= 2
    return order


def impose() -> str:
    src = CFG.output_pdf
    if not src.exists():
        raise FileNotFoundError(f"{src} not found; run assemble first")
    reader = PdfReader(str(src))
    pages = list(reader.pages)
    n = len(pages)
    w = float(pages[0].mediabox.width)
    h = float(pages[0].mediabox.height)

    total = n + (-n % 4)  # pad up to a multiple of 4
    writer = PdfWriter()
    for li, ri in _saddle_order(total):
        sheet = PageObject.create_blank_page(width=2 * w, height=h)
        if li < n:
            sheet.merge_transformed_page(pages[li], Transformation().translate(0, 0))
        if ri < n:
            sheet.merge_transformed_page(pages[ri], Transformation().translate(w, 0))
        writer.add_page(sheet)

    out = CFG.booklet_pdf
    n_sheets = len(writer.pages)
    with open(out, "wb") as f:
        writer.write(f)
    writer.close()
    blanks = total - n
    print(f"[impose] {n} pages -> {n_sheets} 2-up sheets "
          f"({blanks} blank{'s' if blanks != 1 else ''} padded) -> {out.name}")
    return str(out)


if __name__ == "__main__":
    impose()
