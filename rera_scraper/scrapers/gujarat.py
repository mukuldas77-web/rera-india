"""GujRERA (Gujarat) — Angular SPA + JSON REST API.

Fully automatic: the API endpoint is sniffed from the portal's own network
traffic at runtime; no manual DevTools capture needed.
"""
from .auto_api import AutoApiScraper


class GujaratScraper(AutoApiScraper):
    CODE = "GJ"
    STATE = "Gujarat"
