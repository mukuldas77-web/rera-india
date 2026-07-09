# Firebase & hosting options for the RERA app

Short answer: **you can use Firebase, but not for the whole thing.** Firebase
Hosting only serves static files — it can't run this Python scraper/API or a
headless browser. So a pure-Firebase build would mean rewriting the backend.
Here are the realistic paths, best first.

## Option A — Cloud Run + Firebase (recommended if you want Firebase)
- Keep this Python backend; deploy it as a container to **Google Cloud Run**
  (same GCP project as Firebase). Cloud Run can run Playwright/Chromium.
- Store data in **Firestore** instead of SQLite (swap `storage.py` for a
  Firestore client) — gives you a managed, scalable DB and realtime updates.
- Use **Firebase Hosting** for the dashboard UI and **Firebase Auth** for login.
- Use **Cloud Scheduler** to trigger the crawl on a cadence.
- Cost: pay-per-use; a small setup is often a few dollars/month.

## Option B — Render / Railway (simplest, no rewrite)
- Push the repo, it runs as-is via the `Procfile`/`Dockerfile`.
- Add a persistent disk for `rera_data.sqlite` and a background worker for the
  scheduler. No code changes. Cheapest to stand up; least "Google-native".

## Option C — Supabase (good middle ground)
- Managed **Postgres** + auth + auto REST API + a nice dashboard.
- Point the scraper at Postgres (swap the SQLite layer). Host the crawler on
  Render/Cloud Run. Better than SQLite for multi-user/concurrent access.

## Why not "just Firebase"
Firebase = Hosting (static) + Firestore/RTDB (data) + Auth + Functions.
Cloud **Functions** have short timeouts and no full browser, so they can't run
long Playwright crawls of 25 portals. The crawler needs a real container
(Cloud Run / a VPS). That's why every option above pairs Firebase-style
front-end/DB with a container for the scraper.

## My recommendation
- Want Google ecosystem + scale + auth → **Option A (Cloud Run + Firestore +
  Firebase Hosting/Auth)**.
- Want it live this week with zero rewrite → **Option B (Render)**, migrate to A
  later if needed.

Either way the scraper and data model already built here are reused; only the
storage layer and hosting change.
