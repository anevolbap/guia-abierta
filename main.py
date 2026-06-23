"""Orchestrate the pipeline 1->9. Run all, or a subset of stages.

  python main.py                 # full run
  python main.py --only grid     # one stage
  python main.py --from transit   # stage and everything after
  python main.py --list          # show stage order

MVP scoping (single barrio, page cap) is controlled in config.yaml.
"""
from __future__ import annotations

import argparse
import time

from config import CFG, validate_crs

STAGES = [
    ("config", "validate CRS + derived geometry", lambda: validate_crs()),
    ("fetch", "download + cache inputs", lambda: _fetch()),
    ("grid", "page fishnet + sub-grid", lambda: _grid()),
    ("street", "street index", lambda: _street()),
    ("landmarks", "OSM POIs + subte stations", lambda: _landmarks()),
    ("transit", "line<->cell cross-reference", lambda: _transit()),
    ("render", "per-page map PDFs", lambda: _render()),
    ("frontmatter", "cover + indices", lambda: _frontmatter()),
    ("assemble", "merge into guiat.pdf", lambda: _assemble()),
]


def _fetch():
    from fetch import fetch_all
    fetch_all()


def _grid():
    from grid import build_grid
    build_grid()


def _street():
    from street_index import build_street_index
    build_street_index()


def _landmarks():
    from landmarks import build_landmarks
    build_landmarks()


def _transit():
    from transit_index import build_transit_index
    build_transit_index()


def _render():
    from render_pages import render_all
    render_all()


def _frontmatter():
    from frontmatter import build_frontmatter
    build_frontmatter()


def _assemble():
    from assemble import assemble
    assemble()


def run(stages):
    for name, desc, fn in stages:
        t0 = time.time()
        print(f"\n=== {name}: {desc} ===")
        fn()
        print(f"--- {name} done in {time.time() - t0:.1f}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="run a single stage")
    ap.add_argument("--from", dest="from_stage", help="run from this stage onward")
    ap.add_argument("--list", action="store_true", help="list stages")
    args = ap.parse_args()

    names = [s[0] for s in STAGES]
    if args.list:
        for n, d, _ in STAGES:
            print(f"  {n:12s} {d}")
        return
    if args.only:
        run([s for s in STAGES if s[0] == args.only])
        return
    if args.from_stage:
        i = names.index(args.from_stage)
        run(STAGES[i:])
        return
    run(STAGES)
    print(f"\nDone. Booklet at {CFG.output_dir / 'guiat.pdf'}")


if __name__ == "__main__":
    main()
