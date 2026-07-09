"""MahaRERA — largest registry in India (Maharashtra).

Public search: https://maharerait.mahaonline.gov.in/searchlist/searchlist
ASP.NET-style app; results render as an HTML table after selecting filters.
Strategy: iterate divisions/districts so each result set stays paginable,
click through pages, harvest the table.
"""
from datetime import datetime, timezone

from ..base import PlaywrightScraper
from ..models import Project

DIVISIONS = ["Konkan", "Pune", "Nashik", "Nagpur", "Aurangabad", "Amravati"]


class MaharashtraScraper(PlaywrightScraper):
    CODE = "MH"

    def scrape(self):
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        url = self.portal["search_url"]
        with self.browser_page() as page:
            for division in DIVISIONS:
                page.goto(url)
                # NOTE: selector names below match the public search form as of
                # mid-2026; if MahaRERA redesigns, re-inspect with devtools.
                page.select_option("select#Division", label=division)
                page.click("button[type=submit], input[type=submit]")
                page.wait_for_load_state("networkidle")
                while True:
                    for row in self.extract_table(page):
                        yield self._to_project(row, url, now)
                    nxt = page.query_selector("a:has-text('Next'):not(.disabled)")
                    if not nxt:
                        break
                    nxt.click()
                    page.wait_for_load_state("networkidle")

    def _to_project(self, row, url, now):
        get = lambda *keys: next((row[k] for k in keys if k in row and row[k]), "")
        return Project(
            state="Maharashtra",
            rera_reg_no=get("Certificate No", "RERA Registration Number", "Registration No"),
            project_name=get("Project Name", "Name"),
            promoter_name=get("Promoter Name", "Developer"),
            district=get("District"),
            locality=get("Location", "Taluka"),
            status="Registered",
            source_url=url,
            scraped_at=now,
            extra=row,
        )
