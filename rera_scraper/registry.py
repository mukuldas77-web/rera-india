"""Auto-discovering scraper registry.

Every module in rera_scraper/scrapers/ that defines a BaseScraper subclass with
a CODE attribute is registered automatically. To add a state, drop a new module
in scrapers/ (or add a class to an existing one) - no edits here needed.
"""
import importlib
import pkgutil

from .base import BaseScraper
from . import scrapers as _scrapers_pkg

SCRAPERS = {}

for _info in pkgutil.iter_modules(_scrapers_pkg.__path__):
    if _info.name.startswith("_"):
        continue
    try:
        _mod = importlib.import_module("." + "scrapers." + _info.name, __package__)
    except Exception:
        continue
    for _attr in dir(_mod):
        _obj = getattr(_mod, _attr)
        if (isinstance(_obj, type) and issubclass(_obj, BaseScraper)
                and _obj is not BaseScraper and getattr(_obj, "CODE", None)):
            SCRAPERS[_obj.CODE] = _obj


def get_scraper(code):
    if code not in SCRAPERS:
        raise KeyError("No scraper for " + str(code) + ". Available: " + str(sorted(SCRAPERS)))
    return SCRAPERS[code]()
