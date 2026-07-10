"""JHARERA (Jharkhand) - validated live July 2026.

/Home/OnlineRegisteredProjectsList?page=N is a plain server-rendered HTML table
(no JS, no CAPTCHA), ~1,192 registered projects across ~120 pages of 10.
Columns: Sl.No | Reg No & Date | Project Name | Address | Remark | Location.
Uses plain requests + BeautifulSoup (no browser needed).
"""
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from ..base import BaseScraper
from ..models import Project

BASE = "https://jharera.jharkhand.gov.in/Home/OnlineRegisteredProjectsList?page={}"
MAX_PAGES = 300


def _looks_like_date(tok):
    sep = "/" if "/" in tok else ("-" if "-" in tok else "")
    if not sep:
        return False
    parts = tok.split(sep)
    return len(parts) == 3 and all(p.isdigit() for p in parts)


def _parse_regcell(text):
    reg, date = "", ""
    for tok in text.split():
        if tok.upper().startswith("JHARERA"):
            reg = tok
        elif _looks_like_date(tok):
            date = tok
    return (reg or text.strip()), date


class JharkhandScraper(BaseScraper):
    CODE = "JH"

    def scrape(self):
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        seen = set()
        for page_no in range(1, MAX_PAGES + 1):
            html = self.get(BASE.format(page_no)).text
            soup = BeautifulSoup(html, "html.parser")
            table = soup.find("table")
            if not table:
                break
            body = table.find("tbody") or table
            rows = [tr for tr in body.find_all("tr") if tr.find_all("td")]
            if not rows:
                break
            new_on_page = 0
            for tr in rows:
                tds = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
                if len(tds) < 4:
                    continue
                reg, date = _parse_regcell(tds[1])
                if not reg or reg in seen:
                    continue
                seen.add(reg)
                new_on_page += 1
                yield Project(
                    state="Jharkhand",
                    rera_reg_no=reg,
                    project_name=tds[2] if len(tds) > 2 else "",
                    address=tds[3] if len(tds) > 3 else "",
                    status="Registered",
                    approved_on=date,
                    source_url=BASE.format(page_no),
                    scraped_at=now,
                    extra={"raw": tds},
                )
            if new_on_page == 0:
                break
