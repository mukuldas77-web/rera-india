"""HARERA Gurugram — PHP page with an AJAX-fed DataTable.

https://hareraggm.gov.in/en/Project_Certificate.php renders empty table
headers (verified July 2026); rows arrive via an XHR on the same host.
ONE-TIME SETUP: capture the XHR URL from devtools and paste below.
"""
from datetime import datetime, timezone

from ..base import BaseScraper, PlaywrightScraper
from ..models import Project

AJAX_URL = "https://hareraggm.gov.in/PASTE_ENDPOINT_HERE"


class HaryanaGurugramScraper(PlaywrightScraper):
    CODE = "HR-GGM"

    def scrape(self):
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        url = self.portal["search_url"]
        # Playwright fallback works without endpoint capture:
        with self.browser_page() as page:
            page.goto(url)
            page.wait_for_load_state("networkidle")
            # let DataTables show everything if a length selector exists
            sel = page.query_selector("select[name$=_length]")
            if sel:
                sel.select_option(value="-1")
                page.wait_for_load_state("networkidle")
            while True:
                for row in self.extract_table(page):
                    get = lambda *ks: next((row[k] for k in ks if k in row and row[k]), "")
                    yield Project(
                        state="Haryana",
                        rera_reg_no=get("Certificate No"),
                        project_name=get("Project Name"),
                        address=get("Address"),
                        district="Gurugram",
                        status="Registered",
                        source_url=url, scraped_at=now, extra=row,
                    )
                nxt = page.query_selector("a.paginate_button.next:not(.disabled)")
                if not nxt:
                    break
                nxt.click()
                page.wait_for_timeout(800)
