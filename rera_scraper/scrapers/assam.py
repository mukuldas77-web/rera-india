"""RERA Assam - validated live July 2026.

/admincontrol/registered_projects/N is a plain server-rendered HTML table of
registered projects (100 per page, no JS, no CAPTCHA). Paginate N=1,2,... and
parse the table whose header contains "Registration Certificate Number".

Columns: Serial | Reg Cert Number | Project Name | Promoter | Project Location |
Project District | ... | (registration / valid-upto dates near the end).
"""
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from ..base import BaseScraper
from ..models import Project

BASE = "https://rera.assam.gov.in/admincontrol/registered_projects/{}"
MAX_PAGES = 500


def _pick_table(soup):
    # Two tables share the same header (an empty header-only one and the real
    # data table); pick the one that actually has the most rows.
    best, best_n = None, 0
    for t in soup.find_all("table"):
        head = " ".join(th.get_text(" ", strip=True) for th in t.find_all("th"))
        if "Registration Certificate Number" in head:
            n = len(t.find_all("tr"))
            if n > best_n:
                best, best_n = t, n
    return best


class AssamScraper(BaseScraper):
    CODE = "AS"

    def scrape(self):
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        seen = set()
        last_first = None
        for page_no in range(1, MAX_PAGES + 1):
            html = self.get(BASE.format(page_no)).text
            soup = BeautifulSoup(html, "html.parser")
            table = _pick_table(soup)
            if not table:
                break
            trs = table.find_all("tr")[1:]
            rows = []
            for tr in trs:
                tds = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
                if len(tds) >= 6 and tds[1]:
                    rows.append(tds)
            if not rows:
                break
            first = rows[0][1]
            if first == last_first:
                break
            last_first = first
            produced = 0
            for tds in rows:
                reg = tds[1]
                if not reg or reg in seen:
                    continue
                seen.add(reg)
                produced += 1
                date = ""
                for cell in tds[6:]:
                    parts = cell.split("-")
                    if len(parts) == 3 and all(p.isdigit() for p in parts):
                        date = cell
                        break
                yield Project(
                    state="Assam",
                    rera_reg_no=reg,
                    project_name=tds[2],
                    promoter_name=tds[3],
                    locality=tds[4],
                    district=tds[5],
                    approved_on=date,
                    status="Registered",
                    source_url=BASE.format(page_no),
                    scraped_at=now,
                    extra={"raw": tds},
                )
            if produced == 0:
                break
