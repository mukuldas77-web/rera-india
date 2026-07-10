"""K-RERA (Karnataka) - validated live July 2026.

viewAllProjects is a District-dropdown form; Search POSTs to /projectViewDetails
rendering a jQuery DataTable of ALL that district's projects. Iterate districts,
read the full result set from the DataTable API.
"""
from datetime import datetime, timezone

from ..base import PlaywrightScraper
from ..models import Project

SEARCH_URL = "https://rera.karnataka.gov.in/viewAllProjects"


class KarnatakaScraper(PlaywrightScraper):
    CODE = "KA"
    DISTRICTS = None
    STATUS_FILTER = {"APPROVED"}

    def scrape(self):
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        seen = set()
        with self.browser_page() as page:
            page.goto(SEARCH_URL)
            page.wait_for_load_state("networkidle")
            districts = self.DISTRICTS or page.eval_on_selector_all(
                "select[name=district] option",
                "els => els.map(function(e){return e.value;}).filter(function(v){return v && v !== '0';})")
            for dist in districts:
                try:
                    rows = self._fetch_district(page, dist)
                except Exception:
                    continue
                for r in rows:
                    status = (r.get("status") or "").split(" ")[0].upper()
                    if self.STATUS_FILTER and status not in self.STATUS_FILTER:
                        continue
                    key = r.get("reg") or r.get("ack")
                    if not key or key in seen:
                        continue
                    seen.add(key)
                    yield Project(
                        state="Karnataka",
                        rera_reg_no=r.get("reg") or r.get("ack") or "",
                        project_name=r.get("name", ""),
                        promoter_name=r.get("promoter", ""),
                        district=r.get("district", "") or dist,
                        locality=r.get("taluk", ""),
                        project_type=r.get("ptype", ""),
                        status="Registered" if status == "APPROVED" else status.title(),
                        approved_on=r.get("approved", ""),
                        proposed_completion=r.get("completion", ""),
                        source_url=SEARCH_URL, scraped_at=now, extra=r,
                    )

    def _fetch_district(self, page, district):
        page.goto(SEARCH_URL)
        page.wait_for_load_state("networkidle")
        page.select_option("select[name=district]", value=district)
        page.click("button:has-text('Search'), input[type=submit]")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1500)
        return page.evaluate("""function(){
            if (!(window.$ && $.fn && $.fn.dataTable)) return [];
            function clean(h){ var d=document.createElement('div'); d.innerHTML=h;
                return d.textContent.trim(); }
            var dt = $('table').DataTable();
            return dt.rows().data().toArray().map(function(r){ return {
                ack: clean(r[1]), reg: clean(r[2]), promoter: clean(r[4]),
                name: clean(r[5]), status: clean(r[6]), district: clean(r[7]),
                taluk: clean(r[8]), ptype: clean(r[9]), approved: clean(r[11]),
                completion: clean(r[12] || '') }; });
        }""")


# ---- Chhattisgarh (co-located due to GitHub web new-file limitation) ----
URL = "https://rera.cgstate.gov.in/approved_project_list.aspx"


class ChhattisgarhScraper(PlaywrightScraper):
    CODE = "CG"

    def scrape(self):
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self.browser_page() as page:
            page.goto(URL)
            page.wait_for_load_state("networkidle")
            page.wait_for_function(
                "() => window.$ && $.fn.dataTable && "
                "$.fn.dataTable.isDataTable('#ContentPlaceHolder1_gv_ProjectList') && "
                "$('#ContentPlaceHolder1_gv_ProjectList').DataTable().rows().count() > 0",
                timeout=60000)
            rows = page.evaluate("""function(){
                function clean(h){ var d=document.createElement('div'); d.innerHTML=h;
                    return d.textContent.trim(); }
                var dt = $('#ContentPlaceHolder1_gv_ProjectList').DataTable();
                return dt.rows().data().toArray().map(function(r){ return {
                    name: clean(r[1]), reg: clean(r[2]), authorised: clean(r[3]),
                    promoter: clean(r[4]), ptype: clean(r[5]), district: clean(r[6]),
                    tehsil: clean(r[7]), approved: clean(r[8]), end: clean(r[9]),
                    status: clean(r[12] || '') }; });
            }""")
        seen = set()
        for r in rows:
            key = r.get("reg")
            if not key or key in seen:
                continue
            seen.add(key)
            yield Project(
                state="Chhattisgarh",
                rera_reg_no=r.get("reg", ""),
                project_name=r.get("name", ""),
                promoter_name=r.get("promoter") or r.get("authorised", ""),
                district=r.get("district", ""),
                locality=r.get("tehsil", ""),
                project_type=r.get("ptype", ""),
                status=r.get("status") or "Registered",
                approved_on=r.get("approved", ""),
                proposed_completion=r.get("end", ""),
                source_url=URL, scraped_at=now, extra=r,
            )
