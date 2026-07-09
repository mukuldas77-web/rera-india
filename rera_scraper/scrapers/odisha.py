"""ORERA (Odisha) — fully automatic, unattended.

The portal is an Angular SPA whose JSON API signs each request with a
per-payload token (anti-bot), so we don't replay the API. Instead we drive
the real page headlessly with Playwright and harvest the rendered project
cards, clicking through all ~121 pages. This is robust to their token scheme
and needs no manual step. Verified live July 2026 (1,207 registered projects).
"""
import re
from datetime import datetime, timezone

from ..base import PlaywrightScraper
from ..models import Project

REG_RE = re.compile(r"\b[A-Z]{2}/\d+/\d{4}/\d+\b")


class OdishaScraper(PlaywrightScraper):
    CODE = "OD"

    def scrape(self):
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        url = self.portal["search_url"]
        seen = set()
        with self.browser_page() as page:
            page.goto(url)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            while True:
                for rec in self._parse_cards(page):
                    if rec["reg"] and rec["reg"] not in seen:
                        seen.add(rec["reg"])
                        yield Project(
                            state="Odisha", rera_reg_no=rec["reg"],
                            project_name=rec["name"], promoter_name=rec["promoter"],
                            district=rec["district"], project_type=rec["ptype"],
                            approved_on=rec["started"], total_units=rec["units"],
                            status="Registered", source_url=url, scraped_at=now,
                            detail_url=rec.get("detail",""),
                        )
                if not self._next(page):
                    break
                page.wait_for_timeout(1500)

    def _parse_cards(self, page):
        return page.evaluate(r"""() => {
            const R = /\b[A-Z]{2}\/\d+\/\d{4}\/\d+\b/;
            return [...document.querySelectorAll('.card')]
              .filter(c => R.test(c.innerText)).map(c => {
                const t = c.innerText;
                const g = (re) => ((t.match(re)||[,''])[1]||'').trim();
                return {
                  reg: (t.match(R)||[''])[0].trim(),
                  name: (t.split('\n')[0]||'').trim(),
                  promoter: g(/\nby\s+(.+)/),
                  district: g(/Address\s*\n?\s*([^\n]+)/),
                  ptype: g(/Project Type\s*\n?\s*([^\n]+)/),
                  started: g(/Started From\s*\n?\s*([^\n]+)/),
                  units: (t.match(/(\d+)\s*Units/)||[,''])[1],
                  detail: (c.querySelector('a[href*="project"]')||{}).href||''
                };
              });
        }""")

    def _next(self, page):
        return page.evaluate(r"""() => {
            const li = [...document.querySelectorAll('ul.pagination li')]
                .find(e => /Next/i.test(e.innerText));
            if (!li || li.className.includes('disabled')) return false;
            const a = li.querySelector('a,button') || li;
            ['mousedown','mouseup','click'].forEach(ev =>
                a.dispatchEvent(new MouseEvent(ev,{bubbles:true,cancelable:true,view:window})));
            return true;
        }""")
