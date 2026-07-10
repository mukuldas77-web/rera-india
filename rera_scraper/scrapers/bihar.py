"""RERA Bihar - validated live July 2026.

RegisteredPP.aspx is an ASP.NET GridView (GV_Building) of registered projects,
no CAPTCHA. Pagination is via __doPostBack(... 'Page$N'). Driven with Playwright,
harvesting the table on each page until it stops advancing.

Columns: Project Name | Registration No. | Promoter Name | Project Address |
Date of Registration.
"""
from datetime import datetime, timezone

from ..base import PlaywrightScraper
from ..models import Project

URL = "https://rera.bihar.gov.in/RegisteredPP.aspx"
GV = "ctl00$ContentPlaceHolder1$GV_Building"
TABLE = "#ContentPlaceHolder1_GV_Building"
MAX_PAGES = 2000


class BiharScraper(PlaywrightScraper):
    CODE = "BR"

    def scrape(self):
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        seen = set()
        with self.browser_page() as page:
            page.goto(URL)
            page.wait_for_load_state("networkidle")
            page.wait_for_selector(TABLE + " tbody tr", timeout=60000)
            last_first = None
            for n in range(1, MAX_PAGES + 1):
                if n > 1:
                    try:
                        page.evaluate(
                            "function(a){ __doPostBack(a[0], a[1]); }",
                            [GV, "Page$" + str(n)])
                        page.wait_for_load_state("networkidle")
                        page.wait_for_timeout(800)
                    except Exception:
                        break
                rows = self._harvest(page)
                if not rows:
                    break
                first = rows[0].get("reg") or rows[0].get("name")
                if first and first == last_first:
                    break
                last_first = first
                produced = 0
                for r in rows:
                    key = r.get("reg") or (r.get("name", "") + "|" + r.get("date", ""))
                    if not key or key in seen:
                        continue
                    seen.add(key)
                    produced += 1
                    yield Project(
                        state="Bihar",
                        rera_reg_no=r.get("reg", ""),
                        project_name=r.get("name", ""),
                        promoter_name=r.get("promoter", ""),
                        address=r.get("address", ""),
                        approved_on=r.get("date", ""),
                        status="Registered",
                        source_url=URL, scraped_at=now, extra=r,
                    )
                if produced == 0:
                    break

    def _harvest(self, page):
        return page.evaluate("""function(sel){
            function clean(h){ var d=document.createElement('div'); d.innerHTML=h;
                return d.textContent.trim(); }
            var trs = document.querySelectorAll(sel + ' tbody tr');
            var out = [];
            trs.forEach(function(tr){
                var tds = tr.querySelectorAll('td');
                if (tds.length < 4) return;
                out.push({ name: clean(tds[0].innerHTML), reg: clean(tds[1].innerHTML),
                    promoter: clean(tds[2].innerHTML), address: clean(tds[3].innerHTML),
                    date: tds[4] ? clean(tds[4].innerHTML) : '' });
            });
            return out;
        }""", TABLE)
