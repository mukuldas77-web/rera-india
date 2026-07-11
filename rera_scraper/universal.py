"""Universal, Scrapling-powered listing scraper.

Point it at almost any listing/table URL and it extracts structured rows with
minimal (often zero) configuration, using Scrapling for resilience:
  - Fetcher        : fast static HTML (no browser)
  - DynamicFetcher : JS-rendered pages / DataTables (real browser)
  - StealthyFetcher: anti-bot / Cloudflare-protected sites
  - adaptive=True  : selectors that survive website redesigns

Install once (on the machine / CI that runs it):
    pip install -r requirements-universal.txt
    scrapling install            # downloads the browser binaries

Usage (CLI):
    python -m rera_scraper.universal "https://site/list" --mode auto --pages 200
    python -m rera_scraper.universal "https://site/list?page={page}" --mode paged
Usage (library):
    from rera_scraper.universal import UniversalScraper
    rows = UniversalScraper("https://site/list").scrape()   # -> list[dict]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time


def _fetch(url, engine="auto", stealth=False, network_idle=True):
    """Return a Scrapling page object using the lightest engine that works."""
    from scrapling.fetchers import Fetcher, DynamicFetcher, StealthyFetcher

    if stealth:
        StealthyFetcher.adaptive = True
        return StealthyFetcher.fetch(url, headless=True, network_idle=network_idle)
    if engine == "static":
        Fetcher.adaptive = True
        return Fetcher.get(url, stealthy_headers=True)
    if engine == "dynamic":
        DynamicFetcher.adaptive = True
        return DynamicFetcher.fetch(url, headless=True, network_idle=network_idle)

    # auto: try fast static first, fall back to a real browser if it looks empty
    try:
        Fetcher.adaptive = True
        page = Fetcher.get(url, stealthy_headers=True)
        if _count_rows(page) >= 3:
            return page
    except Exception:
        pass
    DynamicFetcher.adaptive = True
    return DynamicFetcher.fetch(url, headless=True, network_idle=network_idle)


def _biggest_table(page):
    """Return the <table> element with the most data rows (Scrapling element)."""
    best, best_n = None, 0
    for t in page.css("table"):
        n = len(t.css("tr"))
        if n > best_n:
            best, best_n = t, n
    return best


def _count_rows(page):
    t = _biggest_table(page)
    return len(t.css("tbody tr") or t.css("tr")) if t else 0


def _table_to_rows(table):
    """Extract a table as list[dict] using header cells as keys."""
    headers = ([h.get_all_text(strip=True) for h in table.css("thead th")]
               or [h.get_all_text(strip=True) for h in table.css("tr th")])
    body = table.css("tbody tr") or table.css("tr")
    rows = []
    for tr in body:
        cells = tr.css("td")
        if not cells:
            continue
        vals = [c.get_all_text(strip=True) for c in cells]
        if headers and len(headers) == len(vals):
            rows.append({headers[i] or ("col" + str(i)): vals[i] for i in range(len(vals))})
        else:
            rows.append({("col" + str(i)): v for i, v in enumerate(vals)})
    return rows


class UniversalScraper:
    """Config-optional scraper. In auto mode it just finds the biggest table
    and paginates by incrementing a {page} placeholder or a ?page= param."""

    def __init__(self, url, mode="auto", page_param="page", max_pages=500,
                 engine="auto", stealth=False, rate_limit=1.0):
        self.url = url
        self.mode = mode
        self.page_param = page_param
        self.max_pages = max_pages
        self.engine = engine
        self.stealth = stealth
        self.rate_limit = rate_limit

    def _page_url(self, n):
        if "{page}" in self.url:
            return self.url.format(page=n)
        sep = "&" if "?" in self.url else "?"
        return self.url + sep + self.page_param + "=" + str(n)

    def scrape(self):
        seen_keys = set()
        out = []
        if self.mode in ("auto", "single"):
            page = _fetch(self.url, self.engine, self.stealth)
            table = _biggest_table(page)
            first = _table_to_rows(table) if table else []
            for r in first:
                k = json.dumps(r, sort_keys=True)
                if k not in seen_keys:
                    seen_keys.add(k); out.append(r)
            if self.mode == "single":
                return out
            if first and len(first) >= 25:
                return self._paged(out, seen_keys, start=2)
            if first and len(first) < 25:
                return self._paged(out, seen_keys, start=2)
            return out
        return self._paged(out, seen_keys, start=1)

    def _paged(self, out, seen_keys, start=1):
        last_sig = None
        for n in range(start, self.max_pages + 1):
            time.sleep(self.rate_limit)
            try:
                page = _fetch(self._page_url(n), self.engine, self.stealth)
            except Exception:
                break
            table = _biggest_table(page)
            rows = _table_to_rows(table) if table else []
            if not rows:
                break
            sig = json.dumps(rows[0], sort_keys=True)
            if sig == last_sig:
                break
            last_sig = sig
            added = 0
            for r in rows:
                k = json.dumps(r, sort_keys=True)
                if k not in seen_keys:
                    seen_keys.add(k); out.append(r); added += 1
            if added == 0:
                break
        return out


def main():
    ap = argparse.ArgumentParser(description="Universal Scrapling listing scraper")
    ap.add_argument("url", help="listing URL (use {page} where the page number goes)")
    ap.add_argument("--mode", default="auto", choices=["auto", "single", "paged"])
    ap.add_argument("--engine", default="auto", choices=["auto", "static", "dynamic"])
    ap.add_argument("--stealth", action="store_true", help="use anti-bot StealthyFetcher")
    ap.add_argument("--pages", type=int, default=500)
    ap.add_argument("--out", default="output.csv")
    args = ap.parse_args()

    rows = UniversalScraper(args.url, mode=args.mode, engine=args.engine,
                            stealth=args.stealth, max_pages=args.pages).scrape()
    print("scraped " + str(len(rows)) + " rows", file=sys.stderr)
    if not rows:
        return
    if args.out.endswith(".json"):
        json.dump(rows, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    else:
        keys = list({k for r in rows for k in r})
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
    print("wrote " + args.out, file=sys.stderr)


if __name__ == "__main__":
    main()
