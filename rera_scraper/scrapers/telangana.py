"""TG RERA (Telangana) — ~11,000 registered projects (July 2026).

Search app: https://rerait.telangana.gov.in/SearchList/Search  (JS-rendered)
Strategy: open search, submit with broad criteria (all districts), paginate.
"""
from datetime import datetime, timezone

from ..base import PlaywrightScraper
from ..models import Project


class TelanganaScraper(PlaywrightScraper):
    CODE = "TG"

    def scrape(self):
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        url = self.portal["search_url"]
        with self.browser_page() as page:
            page.goto(url)
            page.wait_for_load_state("networkidle")
            # Select 'Project' search type if the form offers Project/Agent toggle
            toggle = page.query_selector("input[value=Project], #rbProject")
            if toggle:
                toggle.click()
            page.click("button:has-text('Search'), input[type=submit]")
            page.wait_for_load_state("networkidle")
            while True:
                for row in self.extract_table(page):
                    get = lambda *ks: next((row[k] for k in ks if k in row and row[k]), "")
                    yield Project(
                        state="Telangana",
                        rera_reg_no=get("Registration No", "RERA Regn. No", "Reg No"),
                        project_name=get("Project Name", "Name of Project"),
                        promoter_name=get("Promoter Name", "Developer Name"),
                        district=get("District"),
                        locality=get("Mandal", "Locality"),
                        status="Registered",
                        source_url=url, scraped_at=now, extra=row,
                    )
                nxt = page.query_selector("a:has-text('Next'):not([disabled])")
                if not nxt:
                    break
                nxt.click()
                page.wait_for_load_state("networkidle")
