"""TNRERA (Tamil Nadu) — JS-rendered site; also publishes consolidated
registered/approved project lists as downloadable files.

Strategy: render the registered-projects section with Playwright, harvest the
table; if the page instead links XLSX/PDF lists, download and parse XLSX.
"""
import io
from datetime import datetime, timezone

import pandas as pd

from ..base import PlaywrightScraper
from ..models import Project


class TamilNaduScraper(PlaywrightScraper):
    CODE = "TN"

    def scrape(self):
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        url = self.portal["search_url"]
        with self.browser_page() as page:
            page.goto(url)
            page.wait_for_load_state("networkidle")
            rows = self.extract_table(page)
            if rows:
                for row in rows:
                    yield self._from_row(row, url, now)
                return
            # fallback: look for downloadable XLSX lists
            links = page.eval_on_selector_all(
                "a[href$='.xlsx'], a[href$='.xls']", "els => els.map(e => e.href)")
        for href in links:
            content = self.get(href).content
            df = pd.read_excel(io.BytesIO(content))
            for row in df.fillna("").astype(str).to_dict("records"):
                yield self._from_row(row, href, now)

    def _from_row(self, row, src, now):
        get = lambda *ks: next((row[k] for k in ks if k in row and row[k]), "")
        return Project(
            state="Tamil Nadu",
            rera_reg_no=get("Registration No", "RERA Regn No", "Approval No"),
            project_name=get("Project Name", "Name of the Project"),
            promoter_name=get("Promoter Name", "Name of the Promoter"),
            district=get("District"),
            status="Registered",
            source_url=src, scraped_at=now, extra=row,
        )
