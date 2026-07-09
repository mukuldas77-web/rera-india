"""Fully-automatic scraper for SPA portals (Angular/React + JSON API).

No manual endpoint capture needed: opens the portal's project-list page in
headless Chromium, sniffs the JSON API call the page itself makes, then
paginates that API directly (same browser context = same cookies/headers).
"""
import json as jsonlib
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit, parse_qs, urlencode, urlunsplit

from ..base import PlaywrightScraper, find_project_list, log
from ..models import Project

PAGE_KEYS = re.compile(r"^(page|pageno|page_no|pagenumber|pageindex|start|offset|skip)$", re.I)


class AutoApiScraper(PlaywrightScraper):
    """Subclass: set CODE, STATE and (optionally) override map_item()."""
    STATE = ""
    MAX_PAGES = 2000

    def scrape(self):
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        list_url = self.portal["search_url"].replace("/#/", "/#/")
        with self.browser_page() as page:
            info, first = self.sniff_api(page, list_url)
            if not info:
                # fallback: harvest whatever table rendered
                log.warning("%s: no JSON API detected, falling back to table harvest", self.CODE)
                for row in self.extract_table(page):
                    yield self.map_item(row, list_url, now)
                return

            seen_first_ids = None
            for page_no in range(1, self.MAX_PAGES + 1):
                data = first if page_no == 1 else self._fetch_page(page, info, page_no)
                items = find_project_list(data)
                if not items:
                    break
                if seen_first_ids == jsonlib.dumps(items[0], sort_keys=True, default=str):
                    break  # pagination not advancing
                seen_first_ids = jsonlib.dumps(items[0], sort_keys=True, default=str)
                for it in items:
                    yield self.map_item(it, info["url"], now)
                log.info("%s: page %d -> %d records", self.CODE, page_no, len(items))

    def _fetch_page(self, page, info, page_no):
        """Re-issue the captured API request with the page number advanced."""
        url, method, post = info["url"], info["method"], info["post_data"]
        if post:
            try:  # JSON body
                body = jsonlib.loads(post)
                body = self._bump(body, page_no)
                resp = page.request.fetch(url, method=method,
                                          data=jsonlib.dumps(body),
                                          headers=info["headers"])
            except (ValueError, TypeError):  # form-encoded body
                pairs = {k: v[0] for k, v in parse_qs(post).items()}
                pairs = self._bump(pairs, page_no)
                resp = page.request.fetch(url, method=method, form=pairs)
        else:  # pagination in query string
            parts = urlsplit(url)
            q = {k: v[0] for k, v in parse_qs(parts.query).items()}
            q = self._bump(q, page_no)
            url2 = urlunsplit(parts._replace(query=urlencode(q)))
            resp = page.request.fetch(url2, method=method)
        return resp.json()

    @staticmethod
    def _bump(params: dict, page_no: int) -> dict:
        out = dict(params)
        hit = False
        for k in list(out):
            if PAGE_KEYS.match(str(k)):
                base = out[k]
                if str(k).lower() in ("start", "offset", "skip"):
                    size = int(out.get("length") or out.get("pageSize")
                               or out.get("per_page") or 100)
                    out[k] = type_keep(base, (page_no - 1) * size)
                else:
                    out[k] = type_keep(base, page_no)
                hit = True
        if not hit:
            out["page"] = page_no  # last-resort guess
        return out

    def map_item(self, it: dict, src: str, now: str) -> Project:
        """Best-effort generic field mapping; portal-specific keys land in extra."""
        low = {str(k).lower().replace("_", "").replace(" ", ""): v
               for k, v in it.items()}

        def pick(*names):
            for n in names:
                v = low.get(n)
                if v not in (None, ""):
                    return str(v)
            return ""

        return Project(
            state=self.STATE,
            rera_reg_no=pick("regno", "registrationno", "projregno", "regdno",
                             "registrationnumber", "reranumber", "certificateno"),
            project_name=pick("projectname", "projname", "nameofproject", "name"),
            promoter_name=pick("promotername", "developername", "promoter"),
            district=pick("district", "distname", "districtname"),
            locality=pick("locality", "mandal", "taluka", "village", "location"),
            project_type=pick("projecttype", "typeofproject", "type"),
            status=pick("projectstatus", "status", "appstatus") or "Registered",
            approved_on=pick("approvedon", "approveddate", "registrationdate", "regdate"),
            proposed_completion=pick("completiondate", "proposedcompletiondate",
                                     "proposedend", "enddate"),
            source_url=src, scraped_at=now, extra=it,
        )


def type_keep(original, value):
    """Keep the original param's type (int vs str) when substituting."""
    return value if isinstance(original, int) else str(value)
