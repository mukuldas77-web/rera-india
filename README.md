# Pan-India RERA Scraper

Scrapes registered & upcoming real-estate projects (societies) from state RERA
portals across India into one SQLite database, with Excel/CSV export and
new-registration diffing for recurring runs.

## Why this architecture

There is **no single national RERA database** — every state/UT runs its own
portal on different tech (verified July 2026):

| Portal type | Examples | Approach |
|---|---|---|
| Angular SPA + JSON REST API | Gujarat (GujRERA), Odisha (ORERA) | Direct API calls (fastest) — capture endpoint once via devtools |
| ASP.NET postback (`__VIEWSTATE`) | Maharashtra, UP, AP, MP, Rajasthan | Playwright headless browser |
| Java/Spring POST forms | Karnataka (K-RERA) | Playwright |
| PHP + AJAX DataTables | HARERA Gurugram | Playwright (or captured AJAX URL) |
| Static/CMS pages | Kerala, Delhi, smaller states | Plain requests + BeautifulSoup |
| No online registry | Arunachal, Meghalaya, Mizoram, Nagaland, Sikkim | Manual / RTI |
| CAPTCHA-gated | Rajasthan, HRERA Panchkula | Playwright headed mode (solve once per session) |

`portals.json` is the registry of all 33 portals with URLs, tech
classification, and per-portal notes.

## Setup

```bash
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

## Usage (advanced CLI)

```bash
python -m rera_scraper.cli --list                 # coverage matrix
python -m rera_scraper.cli --states MH TG KA      # scrape selected states
python -m rera_scraper.cli --all                  # all implemented states
python -m rera_scraper.cli --export rera.xlsx     # export DB (one sheet per state)
python -m rera_scraper.cli --new-since 2026-07-01 # newly registered since a date
```

Recurring updates: re-running the same command upserts into SQLite. Rows are
keyed on `(state, rera_reg_no)`; anything not seen before is reported as NEW.
Schedule with cron / Task Scheduler, e.g. daily 6am:
`0 6 * * * cd /path/to/rera-scraper && venv/bin/python -m rera_scraper.cli --all --export rera.xlsx`

## One-command run (fully automatic)

```bash
python run.py            # scrape all implemented states -> SQLite + rera_projects.xlsx
python run.py MH TG      # subset
```

- **GJ, OD** (SPA portals) auto-discover their JSON API at runtime by
  sniffing the portal's own network traffic — no manual endpoint capture.
- **MH, TG, KA, UP, HR-GGM, TN** run headless Playwright against the public
  search pages. Selectors may need a one-time adjustment if a portal
  redesigns (each file notes where).

## Adding a new state (10–30 lines)

1. Look up the portal in `portals.json`.
2. Create `rera_scraper/scrapers/<state>.py` subclassing `PlaywrightScraper`
   (JS-heavy) or `BaseScraper` (plain HTML / API). Yield `Project` records.
3. Register the class in `rera_scraper/registry.py`.

## Data model

Canonical fields per project: state, RERA registration number, project name,
status, promoter name/address/contact, project type, district, locality,
address, pincode, approval & proposed-completion dates, units, area, detail
URL, source URL, scrape timestamp — plus `extra` (JSON) preserving every
portal-specific column so no data is dropped.

## Ground rules baked in

- 2s rate limit between requests per portal (be polite — these are public
  government services); retries with exponential backoff.
- RERA data is public information published under the RERA Act 2016 for
  transparency. Still: respect each site's terms of use, don't hammer
  servers, and prefer published bulk downloads (e.g. TNRERA XLSX lists)
  where offered.

## Known limitations

- Rajasthan & HRERA Panchkula use CAPTCHAs → run those with `HEADLESS = False`
  and solve manually once per run.
- Five NE/Himalayan states have no online project registry to scrape.
- West Bengal: scrape WBRERA (rera.wb.gov.in) — the old HIRA portal was
  scrapped after the 2021 Supreme Court ruling.
- "Upcoming" projects: most portals only expose *approved* registrations;
  a few (e.g. MahaRERA) also list *applied* projects — where available the
  scraper captures the status column so you can filter `status = Applied`.
