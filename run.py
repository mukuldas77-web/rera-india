#!/usr/bin/env python3
"""ONE-COMMAND RUN: scrape every implemented state, save DB, export Excel,
and print newly registered projects since the last run.

    python run.py            # everything
    python run.py MH TG      # only these states
"""
import sys
from datetime import datetime, timezone

from rera_scraper.base import load_portals
from rera_scraper.registry import SCRAPERS, get_scraper
from rera_scraper.storage import Store

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("rera")


def main():
    codes = sys.argv[1:] or sorted(SCRAPERS)
    portals = load_portals()
    store = Store("rera_data.sqlite")
    run_started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    summary = {}
    for code in codes:
        try:
            log.info("=== %s (%s) ===", portals[code]["state"], code)
            result = store.upsert(get_scraper(code).scrape())
            summary[code] = f"{len(result['new'])} new / {result['updated']} updated"
        except Exception as e:
            summary[code] = f"FAILED: {e}"
            log.exception("%s failed; continuing", code)

    path, n = store.export("rera_projects.xlsx")
    print("\n================ RUN SUMMARY ================")
    for code, s in summary.items():
        print(f"  {code:8} {s}")
    print(f"  Exported {n} total rows -> {path}")
    new_df = store.new_since(run_started)
    if len(new_df):
        print(f"\n  {len(new_df)} NEWLY REGISTERED since last run:")
        print(new_df[["state", "rera_reg_no", "project_name", "district"]]
              .head(50).to_string(index=False))


if __name__ == "__main__":
    main()
