# RERA India Scraper + Dashboard — Start Here

You have three ways to run this, all working. **Pick the free one.**

## 🟢 FREE, automatic, always-on  → read FREE_HOSTING.md
GitHub Actions runs the scraper on a schedule; GitHub Pages hosts the dashboard.
No credit card, no server bill. Best for "set it and forget it."
- Dashboard: `docs/index.html` (loads `docs/projects.json`, filters in-browser)
- Schedule:  `.github/workflows/crawl.yml`

## �df Run on your own PC (private, $0, only when PC is on)
```bash
pip install -r requirements.txt
playwright install chromium
python run.py                 # scrape all implemented states -> SQLite + Excel
python export_json.py         # refresh the static dashboard data
```
Open `docs/index.html` in your browser. Automate with Windows Task Scheduler.

## 🌐 Full server app (FastAPI + live search API + scheduler)  → webapp/README.md
For when you want a hosted multi-user app. Deploy free on Oracle Cloud Always
Free, or paid on Render/Cloud Run. See FIREBASE.md for the Firebase/Google path.

---
**What's inside**
- `rera_scraper/`  — modular scraper (8 states live, 33 portals mapped in portals.json)
- `run.py`        — one command: scrape everything, export Excel, report new registrations
- `docs/`         — free static dashboard + real data (218 live Odisha projects)
- `webapp/`       — FastAPI dashboard + API + auto-scheduler
- `sample_data/`  — the 218 real Odisha projects as CSV/XLSX
- Guides: FREE_HOSTING.md · FIREBASE.md · README.md · webapp/README.md

Data currently loaded: **218 real projects** scraped live from ORERA (Odisha),
July 2026. Run the scraper to add the other states.
