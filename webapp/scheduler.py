"""Background scheduler: re-runs scrapers on a cadence so the dashboard stays
current without anyone pressing a button.

Run standalone:   python -m webapp.scheduler
Or import start_scheduler(app) to run inside the web process.
"""
import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from rera_scraper.registry import SCRAPERS, get_scraper
from rera_scraper.storage import Store

log = logging.getLogger("rera.scheduler")
DB = os.environ.get("RERA_DB", "rera_data.sqlite")
# comma-separated codes, or "ALL"
STATES = os.environ.get("RERA_STATES", "ALL")
CRON = os.environ.get("RERA_CRON", "0 3 * * *")  # daily 03:00 by default


def run_all():
    codes = sorted(SCRAPERS) if STATES.upper() == "ALL" else STATES.split(",")
    store = Store(DB)
    for code in codes:
        try:
            log.info("scheduled scrape: %s", code)
            res = store.upsert(get_scraper(code.strip()).scrape())
            log.info("%s: %d new, %d updated", code, len(res["new"]), res["updated"])
        except Exception:
            log.exception("scheduled scrape failed: %s", code)


def start_scheduler():
    sched = BackgroundScheduler(timezone="Asia/Kolkata")
    sched.add_job(run_all, CronTrigger.from_crontab(CRON), id="rera_crawl",
                  misfire_grace_time=3600, coalesce=True)
    sched.start()
    log.info("scheduler started (cron=%s, states=%s)", CRON, STATES)
    return sched


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_all()
