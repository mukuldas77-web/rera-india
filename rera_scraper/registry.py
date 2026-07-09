"""Maps portal codes to scraper classes. Add new states here."""
from .scrapers.maharashtra import MaharashtraScraper
from .scrapers.telangana import TelanganaScraper
from .scrapers.karnataka import KarnatakaScraper
from .scrapers.gujarat import GujaratScraper
from .scrapers.odisha import OdishaScraper
from .scrapers.uttar_pradesh import UttarPradeshScraper
from .scrapers.haryana_gurugram import HaryanaGurugramScraper
from .scrapers.tamil_nadu import TamilNaduScraper

SCRAPERS = {
    "MH": MaharashtraScraper,
    "TG": TelanganaScraper,
    "KA": KarnatakaScraper,
    "GJ": GujaratScraper,
    "OD": OdishaScraper,
    "UP": UttarPradeshScraper,
    "HR-GGM": HaryanaGurugramScraper,
    "TN": TamilNaduScraper,
}


def get_scraper(code: str):
    if code not in SCRAPERS:
        raise KeyError(
            f"No scraper implemented for '{code}' yet. Implemented: {sorted(SCRAPERS)}. "
            "See portals.json for portal metadata and README for how to add one.")
    return SCRAPERS[code]()
