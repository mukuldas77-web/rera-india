"""CLI entry point.

Examples:
  python -m rera_scraper.cli --states MH TG KA           # scrape selected states
  python -m rera_scraper.cli --all                        # every implemented state
  python -m rera_scraper.cli --states MH --export out.xlsx
  python -m rera_scraper.cli --new-since 2026-07-01       # report new registrations
  python -m rera_scraper.cli --list                       # show portal coverage
"""
import argparse
import logging
import sys

from .base import load_portals
from .registry import SCRAPERS, get_scraper
from .storage import Store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("rera")


def main():
    ap = argparse.ArgumentParser(description="Pan-India RERA registered-projects scraper")
    ap.add_argument("--states", nargs="+", metavar="CODE", help="portal codes, e.g. MH TG KA")
    ap.add_argument("--all", action="store_true", help="run every implemented scraper")
    ap.add_argument("--db", default="rera_data.sqlite")
    ap.add_argument("--export", metavar="FILE", help="export to .xlsx or .csv after scraping")
    ap.add_argument("--new-since", metavar="YYYY-MM-DD", help="print projects first seen since date")
    ap.add_argument("--list", action="store_true", help="list all portals and coverage status")
    args = ap.parse_args()

    portals = load_portals()

    if args.list:
        for code, p in sorted(portals.items()):
            impl = "IMPLEMENTED" if code in SCRAPERS else "todo"
            print(f"{code:8} {p['state']:28} {impl:12} {p['method']:11} {p['base_url']}")
        return

    store = Store(args.db)

    if args.new_since:
        df = store.new_since(args.new_since)
        print(df[["state", "rera_reg_no", "project_name", "district", "first_seen"]]
              .to_string(index=False) if len(df) else "No new registrations found.")
        return

    codes = sorted(SCRAPERS) if args.all else (args.states or [])
    if not codes and not args.export:
        ap.print_help()
        sys.exit(1)

    for code in codes:
        try:
            scraper = get_scraper(code)
            log.info("=== %s (%s) ===", portals[code]["state"], code)
            result = store.upsert(scraper.scrape())
            log.info("%s: %d new, %d updated (db total %d)",
                     code, len(result["new"]), result["updated"], result["total"])
            for r in result["new"][:20]:
                log.info("  NEW: %s — %s", r["rera_reg_no"], r["project_name"])
        except Exception:
            log.exception("Scraper %s failed; continuing with next state", code)

    if args.export:
        path, n = store.export(args.export)
        log.info("Exported %d rows -> %s", n, path)


if __name__ == "__main__":
    main()
