"""Universal, Scrapling-powered listing scraper.

Point it at almost any listing/table URL and it extracts structured rows,
using Scrapling for resilience (static / dynamic / stealth fetchers + adaptive
selectors). Optionally follows each row's location link to read exact lat/long.
"""
from __future__ import annotations

import argparse
import csv
import json
import re as _re
import sys
import time
from urllib.parse import urljoin


def _fetch(url, engine="auto", stealth=False, network_idle=True):
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
    best, best_n = None, 0
    for t in page.css("table"):
        n = len(t.css("tr"))
        if n > best_n:
            best, best_n = t, n
    return best


def _count_rows(page):
    t = _biggest_table(page)
    return len(t.css("tbody tr") or t.css("tr")) if t else 0


_COORD_RE = _re.compile(r"(-?\d{1,3}\.\d{3,})[ ,/]+(-?\d{1,3}\.\d{3,})")
_LAT_RE = _re.compile(r"lat[a-z]*\s*[:=]\s*['\"]?(-?\d{1,2}\.\d{3,})", _re.I)
_LNG_RE = _re.compile(r"(?:lng|lon|long)[a-z]*\s*[:=]\s*['\"]?(-?\d{2,3}\.\d{3,})", _re.I)
_LATLNG_RE = _re.compile(r"LatLng\(\s*(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)")


def _coords_from_links(hrefs):
    for h in hrefs:
        if not h:
            continue
        u = h.replace("%2C", ",").replace("%20", " ")
        low = u.lower()
        if ("map" not in low and "@" not in u and "q=" not in low and "ll=" not in low):
            continue
        m = _COORD_RE.search(u)
        if m:
            lat, lng = float(m.group(1)), float(m.group(2))
            if -90 <= lat <= 90 and -180 <= lng <= 180:
                return str(lat), str(lng)
    return "", ""


def _html_of(page):
    for attr in ("html_content", "body", "content", "text"):
        v = getattr(page, attr, None)
        if isinstance(v, bytes):
            return v.decode("utf-8", "ignore")
        if isinstance(v, str) and len(v) > 50:
            return v
    return str(page)


def _resolve_coords(url):
    """Fetch a location detail page and read the exact lat/lng off it."""
    from scrapling.fetchers import Fetcher
    try:
        html = _html_of(Fetcher.get(url, stealthy_headers=True))
    except Exception:
        return "", ""
    m = _LATLNG_RE.search(html)
    if m:
        return m.group(1), m.group(2)
    la, ln = _LAT_RE.search(html), _LNG_RE.search(html)
    if la and ln:
        return la.group(1), ln.group(1)
    return "", ""


def _table_to_rows(table):
    """Extract a table as list[dict]. Link cells also yield a '<col> URL'
    column, and lat/long are pulled from any map link in the row."""
    headers = ([h.get_all_text(strip=True) for h in table.css("thead th")]
               or [h.get_all_text(strip=True) for h in table.css("tr th")])
    body = table.css("tbody tr") or table.css("tr")
    rows = []
    for tr in body:
        cells = tr.css("td")
        if not cells:
            continue
        rec, hrefs = {}, []
        for i, c in enumerate(cells):
            key = headers[i] if (headers and i < len(headers) and headers[i]) else ("col" + str(i))
            rec[key] = c.get_all_text(strip=True)
            href = c.css("a::attr(href)").get()
            if href and href.strip() not in ("#", "javascript:;", "javascript:void(0)"):
                rec[key + " URL"] = href.strip()
                hrefs.append(href.strip())
        lat, lng = _coords_from_links(hrefs)
        if lat:
            rec["latitude"], rec["longitude"] = lat, lng
        rows.append(rec)
    return rows


class UniversalScraper:
    def __init__(self, url, mode="auto", page_param="page", max_pages=500,
                 engine="auto", stealth=False, rate_limit=1.0, resolve_coords=False):
        self.url = url
        self.mode = mode
        self.page_param = page_param
        self.max_pages = max_pages
        self.engine = engine
        self.stealth = stealth
        self.rate_limit = rate_limit
        self.resolve_coords = resolve_coords

    def _page_url(self, n):
        if "{page}" in self.url:
            return self.url.format(page=n)
        sep = "&" if "?" in self.url else "?"
        return self.url + sep + self.page_param + "=" + str(n)

    def scrape(self):
        rows = self._scrape_raw()
        if self.resolve_coords:
            self._resolve(rows)
        return rows

    def _resolve(self, rows):
        seen = {}
        for r in rows:
            if r.get("latitude"):
                continue
            locurl = next((v for k, v in r.items()
                           if k.endswith("URL") and any(w in str(v).lower()
                           for w in ("location", "map", "getlocation", "latlong"))), None)
            if not locurl:
                continue
            absu = urljoin(self.url, locurl)
            if absu in seen:
                la, ln = seen[absu]
            else:
                la, ln = _resolve_coords(absu)
                seen[absu] = (la, ln)
                time.sleep(0.3)
            if la:
                r["latitude"], r["longitude"] = la, ln

    def _scrape_raw(self):
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
    ap.add_argument("url")
    ap.add_argument("--mode", default="auto", choices=["auto", "single", "paged"])
    ap.add_argument("--engine", default="auto", choices=["auto", "static", "dynamic"])
    ap.add_argument("--stealth", action="store_true")
    ap.add_argument("--coords", action="store_true", help="resolve exact lat/long")
    ap.add_argument("--pages", type=int, default=500)
    ap.add_argument("--out", default="output.csv")
    args = ap.parse_args()
    rows = UniversalScraper(args.url, mode=args.mode, engine=args.engine,
                            stealth=args.stealth, max_pages=args.pages,
                            resolve_coords=args.coords).scrape()
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
