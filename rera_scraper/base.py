"""Scraper base classes: polite requests session + Playwright browser base."""
import json
import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path

import requests


def retry(attempts=3, base_wait=2.0):
    """Simple exponential-backoff retry decorator."""
    import functools

    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*a, **kw):
            for i in range(attempts):
                try:
                    return fn(*a, **kw)
                except Exception:
                    if i == attempts - 1:
                        raise
                    time.sleep(min(base_wait * 2 ** i, 30))
        return wrapper
    return deco

log = logging.getLogger("rera")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def load_portals():
    p = Path(__file__).resolve().parent.parent / "portals.json"
    return {x["code"]: x for x in json.loads(p.read_text(encoding="utf-8"))["portals"]}


class BaseScraper(ABC):
    """Subclass per state. Set CODE to the portals.json code."""
    CODE = None
    RATE_LIMIT_SECONDS = 2.0   # be polite to government servers

    def __init__(self):
        self.portal = load_portals()[self.CODE]
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": UA, "Accept-Language": "en-IN,en;q=0.9"})
        self._last_request = 0.0

    def _throttle(self):
        wait = self.RATE_LIMIT_SECONDS - (time.time() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.time()

    @retry()
    def get(self, url, **kw):
        self._throttle()
        r = self.session.get(url, timeout=60, **kw)
        r.raise_for_status()
        return r

    @retry()
    def post(self, url, **kw):
        self._throttle()
        r = self.session.post(url, timeout=60, **kw)
        r.raise_for_status()
        return r

    @abstractmethod
    def scrape(self):
        """Yield Project records."""
        ...


class PlaywrightScraper(BaseScraper):
    """Base for JS-rendered portals (most modern RERA sites).

    Usage in subclass:
        def scrape(self):
            with self.browser_page() as page:
                page.goto(self.portal["search_url"])
                ...
    """
    HEADLESS = True

    def browser_page(self):
        from contextlib import contextmanager

        @contextmanager
        def _page():
            from playwright.sync_api import sync_playwright
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=self.HEADLESS)
                ctx = browser.new_context(user_agent=UA, locale="en-IN")
                page = ctx.new_page()
                page.set_default_timeout(60_000)
                try:
                    yield page
                finally:
                    browser.close()
        return _page()

    def extract_table(self, page, table_selector="table"):
        """Generic: pull all rows of the first matching HTML table as list[dict]."""
        return page.evaluate(
            """(sel) => {
                const t = document.querySelector(sel);
                if (!t) return [];
                const headers = [...t.querySelectorAll('thead th, tr:first-child th')]
                    .map(th => th.innerText.trim());
                return [...t.querySelectorAll('tbody tr')].map(tr =>
                    Object.fromEntries([...tr.querySelectorAll('td')].map((td, i) =>
                        [headers[i] || `col${i}`, td.innerText.trim()])));
            }""", table_selector)


    def sniff_api(self, page, list_page_url, url_hint=""):
        """Load an SPA list page and auto-capture the JSON API call that
        returns the project list. Returns (request_info, first_payload).

        request_info: dict(url, method, post_data, headers)
        Picks the JSON response with the largest embedded list.
        """
        captured = []

        def on_response(resp):
            try:
                ct = resp.headers.get("content-type", "")
                if "json" not in ct or (url_hint and url_hint not in resp.url):
                    return
                data = resp.json()
                size = _largest_list_len(data)
                if size >= 1:
                    req = resp.request
                    captured.append(({
                        "url": resp.url, "method": req.method,
                        "post_data": req.post_data,
                        "headers": {k: v for k, v in req.headers.items()
                                    if k.lower() in ("content-type", "accept")},
                    }, data, size))
            except Exception:
                pass

        page.on("response", on_response)
        page.goto(list_page_url)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        if not captured:
            return None, None
        captured.sort(key=lambda x: x[2], reverse=True)
        info, data, _ = captured[0]
        log.info("auto-captured API: %s %s", info["method"], info["url"])
        return info, data


def _largest_list_len(obj, depth=0):
    """Size of the largest list of dicts anywhere in a JSON structure."""
    if depth > 4:
        return 0
    if isinstance(obj, list):
        return len(obj) if obj and isinstance(obj[0], dict) else 0
    if isinstance(obj, dict):
        return max((_largest_list_len(v, depth + 1) for v in obj.values()), default=0)
    return 0


def find_project_list(obj, depth=0):
    """Return the largest list-of-dicts found in a JSON structure."""
    best = []
    if depth > 4:
        return best
    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
        return obj
    if isinstance(obj, dict):
        for v in obj.values():
            cand = find_project_list(v, depth + 1)
            if len(cand) > len(best):
                best = cand
    return best
