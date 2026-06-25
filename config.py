"""Single source of truth. Loads config.yaml into a typed object.

Import `CFG` everywhere. Derived geometry (page size in metres, etc.) is
computed once here so no other module re-derives it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.yaml"


@dataclass
class Config:
    raw: dict[str, Any]

    # --- CRS ---
    crs_work: str = "EPSG:9498"
    crs_geo: str = "EPSG:4326"

    # --- page (mm) ---
    page_w_mm: float = 148
    page_h_mm: float = 210
    margin_left_mm: float = 6
    margin_right_mm: float = 4
    margin_top_mm: float = 12
    margin_bottom_mm: float = 8

    # --- scale ---
    scale_denom: float = 20000

    # --- subgrid ---
    cols: int = 5
    rows: int = 7
    col_labels: str = "ABCDE"
    row_labels: str = "1234567"

    # --- grid filtering ---
    min_land_fraction: float = 0.04
    min_street_len_m: float = 9000
    snap_origin_m: float = 1000

    modes: dict[str, bool] = field(default_factory=dict)
    coverage_gate: dict[str, int] = field(default_factory=dict)
    landmark_categories: dict[str, list] = field(default_factory=dict)
    landmark_large_only: list = field(default_factory=list)
    min_major_area_m2: float = 40000
    number_bucket_step: int = 1000

    mvp_enabled: bool = True
    mvp_barrio: str = "CHACARITA"
    mvp_max_pages: int = 6

    datos_fecha: str = ""
    title: str = "Guía Bondi"
    subtitle: str = "Colectivos y subte · Buenos Aires"
    edition: str = "Edición abierta"
    sources: dict[str, Any] = field(default_factory=dict)

    # paths
    data_dir: Path = ROOT / "data"
    output_dir: Path = ROOT / "output"
    pages_dir: Path = ROOT / "output" / "pages"

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> Config:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        c = cls(raw=raw)
        crs = raw.get("crs", {})
        c.crs_work = crs.get("work", c.crs_work)
        c.crs_geo = crs.get("geographic", c.crs_geo)

        pg = raw.get("page", {})
        c.page_w_mm = pg.get("width_mm", c.page_w_mm)
        c.page_h_mm = pg.get("height_mm", c.page_h_mm)
        c.margin_left_mm = pg.get("margin_left_mm", c.margin_left_mm)
        c.margin_right_mm = pg.get("margin_right_mm", c.margin_right_mm)
        c.margin_top_mm = pg.get("margin_top_mm", c.margin_top_mm)
        c.margin_bottom_mm = pg.get("margin_bottom_mm", c.margin_bottom_mm)

        c.scale_denom = raw.get("scale", {}).get("denominator", c.scale_denom)

        sg = raw.get("subgrid", {})
        c.cols = sg.get("cols", c.cols)
        c.rows = sg.get("rows", c.rows)
        c.col_labels = sg.get("col_labels", c.col_labels)
        c.row_labels = sg.get("row_labels", c.row_labels)

        gr = raw.get("grid", {})
        c.min_land_fraction = gr.get("min_land_fraction", c.min_land_fraction)
        c.min_street_len_m = gr.get("min_street_len_m", c.min_street_len_m)
        c.snap_origin_m = gr.get("snap_origin_m", c.snap_origin_m)

        c.modes = raw.get("modes", {"colectivo": True, "subte": True})
        c.coverage_gate = raw.get("coverage_gate", {})
        lm = raw.get("landmarks", {})
        c.landmark_categories = lm.get("categories", {})
        c.landmark_large_only = lm.get("large_only", [])
        c.min_major_area_m2 = lm.get("min_major_area_m2", c.min_major_area_m2)
        c.number_bucket_step = raw.get("street_index", {}).get(
            "number_bucket_step", c.number_bucket_step)

        mvp = raw.get("mvp", {})
        c.mvp_enabled = mvp.get("enabled", c.mvp_enabled)
        c.mvp_barrio = mvp.get("barrio", c.mvp_barrio)
        c.mvp_max_pages = mvp.get("max_pages", c.mvp_max_pages)

        c.datos_fecha = raw.get("datos_fecha", "")
        bk = raw.get("booklet", {})
        c.title = bk.get("title", c.title)
        c.subtitle = bk.get("subtitle", c.subtitle)
        c.edition = bk.get("edition", c.edition)
        c.sources = raw.get("sources", {})

        paths = raw.get("paths", {})
        c.data_dir = ROOT / paths.get("data", "data")
        c.output_dir = ROOT / paths.get("output", "output")
        c.pages_dir = ROOT / paths.get("pages", "output/pages")
        for d in (c.data_dir, c.output_dir, c.pages_dir):
            d.mkdir(parents=True, exist_ok=True)
        return c

    # ---- derived geometry ----
    @property
    def map_w_mm(self) -> float:
        return self.page_w_mm - self.margin_left_mm - self.margin_right_mm

    @property
    def map_h_mm(self) -> float:
        return self.page_h_mm - self.margin_top_mm - self.margin_bottom_mm

    @property
    def page_w_m(self) -> float:
        """Real-world width covered by the map window, in metres."""
        return self.map_w_mm / 1000.0 * self.scale_denom

    @property
    def page_h_m(self) -> float:
        return self.map_h_mm / 1000.0 * self.scale_denom

    @property
    def cell_w_m(self) -> float:
        return self.page_w_m / self.cols

    @property
    def cell_h_m(self) -> float:
        return self.page_h_m / self.rows

    def cell_ref(self, page: int, col_idx: int, row_idx: int) -> str:
        """Build a 'NN-C4' style reference. col_idx/row_idx are 0-based."""
        return f"{page}-{self.col_labels[col_idx]}{self.row_labels[row_idx]}"

    def mm_to_in(self, mm: float) -> float:
        return mm / 25.4

    @property
    def slug(self) -> str:
        import re
        import unicodedata
        s = unicodedata.normalize("NFKD", self.title).encode("ascii", "ignore").decode()
        s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
        return s or "guia"

    @property
    def output_pdf(self) -> Path:
        return self.output_dir / f"{self.slug}.pdf"

    @property
    def booklet_pdf(self) -> Path:
        return self.output_dir / f"{self.slug}-booklet.pdf"


CFG = Config.load()


def validate_crs() -> None:
    """Fail early if the work CRS is not metric (warped-grid guard)."""
    from pyproj import CRS

    crs = CRS.from_user_input(CFG.crs_work)
    unit = crs.axis_info[0].unit_name
    if "metre" not in unit and "meter" not in unit:
        raise ValueError(
            f"Work CRS {CFG.crs_work} is not metric (unit={unit}); "
            "pages would not share a uniform scale."
        )
    # Sanity: page size must be positive and reasonable (hundreds of metres+).
    assert CFG.page_w_m > 100 and CFG.page_h_m > 100, "page size too small"
    print(
        f"[config] scale 1:{int(CFG.scale_denom)} -> "
        f"page tile {CFG.page_w_m:.0f} x {CFG.page_h_m:.0f} m, "
        f"cell {CFG.cell_w_m:.0f} x {CFG.cell_h_m:.0f} m, "
        f"CRS {CFG.crs_work} ({crs.axis_info[0].unit_name})"
    )


if __name__ == "__main__":
    validate_crs()
