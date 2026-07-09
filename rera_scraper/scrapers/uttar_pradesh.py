"""UP RERA — ASP.NET postback app (__VIEWSTATE), use Playwright.

Public project search page renders a paginated grid after search.
"""
from datetime import datetime, timezone

from ..base import PlaywrightScraper
from ..models import Project


class UttarPradeshScraper(PlaywrightScraper):
    CODE = "UP"

    def scrape(self):
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        url = self.portal["search_url"]
        with self.browser_page() as page:
            page.goto(url)
            page.wait_for_load_state("networkidle")
            btn = page.query_selector("input[type=submit], button:has-text('Search')")
            if btn:
                btn.click()
                page.wait_for_load_state("networkidle")
            while True:
                for row in self.extract_table(page):
                    get = lambda *ks: next((row[k] for k in ks if k in row and row[k]), "")
                    yield Project(
                        state="Uttar Pradesh",
                        rera_reg_no=get("Registration No", "RERA Registration Number"),
                        project_name=get("Project Name"),
                        promoter_name=get("Promoter Name"),
                        district=get("District"),
                        status=get("Status") or "Registered",
                        source_url=url, scraped_at=now, extra=row,
                    )
                nxt = page.query_selector("a:has-text('Next'):not(.aspNetDisabled)")
                if not nxt:
                    break
                nxt.click()
                page.wait_for_load_state("networkidle")
