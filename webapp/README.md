# RERA India — Web Dashboard

A hosted-ready web app over the scraped RERA project database: search/filter by
state, district, promoter, status and date; "new this week" view; Excel export;
and a background scheduler that re-crawls on a cadence.

## Run locally

```bash
pip install -r requirements.txt
playwright install chromium
uvicorn webapp.app:app --reload --port 8000
# open http://localhost:8000
```

The repo ships with `rera_data.sqlite` pre-seeded with 218 real Odisha projects,
so the dashboard has data on first boot. Run `python run.py` (or the scheduler)
to add more states.

## Auto-refresh (scheduler)

```bash
# one-off crawl of all implemented states
python -m webapp.scheduler
# or set a schedule via env and run the scheduler process:
RERA_CRON="0 3 * * *" RERA_STATES=ALL python -m webapp.scheduler
```

Env vars: `RERA_DB` (db path), `RERA_STATES` (`ALL` or `MH,TG,OD`), `RERA_CRON`.

## Deploy to a host

**Render / Railway (easiest):** push this repo to GitHub, create a new Web
Service, and it will read the `Procfile`. Add a persistent disk mounted at
`/data` and set `RERA_DB=/data/rera_data.sqlite`. Add a separate "Background
Worker" running `python -m webapp.scheduler` for auto-crawls.

**Docker (any VPS / cloud):**
```bash
docker build -t rera-app .
docker run -p 8000:8000 -v $PWD/data:/data rera-app
```

**Firebase:** see FIREBASE.md — Firebase Hosting can't run this Python backend
directly; the recommended split is Firestore + Cloud Run, or keep this backend
and use Firebase only for the frontend/auth.

## API

`GET /api/stats` · `GET /api/filters` · `GET /api/projects?state=&district=&promoter=&status=&search=&since=&limit=&offset=`
· `GET /api/export?…` (returns Excel)
