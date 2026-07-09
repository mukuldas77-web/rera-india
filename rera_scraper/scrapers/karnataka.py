"""K-RERA (Karnataka) — Java/Spring app, project list behind POST form.

https://rera.karnataka.gov.in/viewAllProjects
Strategy: load form, iterate district options, submit, paginate result table.
"""
from datetime import datetime, timezone

from ..base import PlaywrightScraper
from ..models import Project


class KarnatakaScraper(PlaywrightScraper):
    CODE = "KA"

    def scrape(self):
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        url = self.portal["search_url"]
        with self.browser_page() as page:
            page.goto(url)
            page.wait_for_load_state("networkidle")
            district_sel = "select#projectDist, select[name=district]"
            options = page.eval_on_selector_all(
                f"{district_sel} option", "els => els.map(e => e.value).filter(v => v)")
            for value in options:
                page.goto(url)
                page.select_option(district_sel, value=value)
                page.click("input[type=submit], button[type=submit]")
                page.wait_for_load_state("networkidle")
                while True:
                    for row in self.extract_table(page):
                        get = lambda *ks: next((row[k] for k in ks if k in row and row[k]), "")
                        yield Project(
                            state="Karnataka",
                            rera_reg_no=get("Registration Number", "Acknowledgement Number", "Reg No"),
                            project_name=get("Project Name"),
                            promoter_name=get("Promoter Name"),
                            district=get("District"),
                            project_type=get("Project Type"),
                            status=get("Status") or "Registered",
                            approved_on=get("Approved Date", "Registration Date"),
                            proposed_completion=get("Completion Date", "Proposed Completion Date"),
                            source_url=url, scraped_at=now, extra=row,
                        )
                    nxt = page.query_selector("a:has-text('Next'):not(.disabled)")
                    if not nxt:
                        break
                    nxt.click()
                    page.wait_for_load_state("networkidle")
