"""MP RERA (Madhya Pradesh) - validated live July 2026.

/all-projects/ loads ALL ~8,400 projects client-side into one jQuery DataTable.
Load the page and read the full set from the DataTable API. List columns:
SN | Project | Promoter | District - Planning Area | Status | Details(link).
RERA number is only on the detail page, so we key on the encoded project id.
"""
import re
from datetime import datetime, timezone

from ..base import PlaywrightScraper
from ..models import Project

URL = "https://rera.mp.gov.in/all-projects/"
NON_REGISTERED = re.compile("reject|withdraw|lapsed|not applied|suspend|revok", re.I)


class MadhyaPradeshScraper(PlaywrightScraper):
    CODE = "MP"
    REGISTERED_ONLY = True

    def scrape(self):
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self.browser_page() as page:
            page.goto(URL)
            page.wait_for_load_state("networkidle")
            page.wait_for_function(
                "() => window.$ && $.fn.dataTable && "
                "$.fn.dataTable.isDataTable('table') && "
                "$('table').DataTable().rows().count() > 50",
                timeout=90000)
            rows = page.evaluate("""function(){
                function clean(h){ var d=document.createElement('div'); d.innerHTML=h;
                    return d.textContent.trim(); }
                function idOf(h){ var m=String(h).match(/id=([A-Za-z0-9=]+)/); return m?m[1]:''; }
                var dt=$('table').DataTable();
                return dt.rows().data().toArray().map(function(r){ return {
                    name: clean(r[1]), promoter: clean(r[2]), district: clean(r[3]),
                    status: clean(r[4]), pid: idOf(r[5]) }; });
            }""")
        seen = set()
        for r in rows:
            status = r.get("status", "")
            if self.REGISTERED_ONLY and NON_REGISTERED.search(status or ""):
                continue
            key = r.get("pid") or (r.get("name", "") + "|" + r.get("promoter", ""))
            if not key or key in seen:
                continue
            seen.add(key)
            district = (r.get("district") or "").split(" - ")[0].strip()
            yield Project(
                state="Madhya Pradesh",
                rera_reg_no=r.get("pid", "") or key,
                project_name=r.get("name", ""),
                promoter_name=r.get("promoter", ""),
                district=district,
                locality=(r.get("district") or ""),
                status=status or "Registered",
                detail_url=("https://www.rera.mp.gov.in/view_project_details.php?id=" + r.get("pid", "")) if r.get("pid") else "",
                source_url=URL, scraped_at=now, extra=r,
            )
