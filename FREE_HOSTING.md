# Run everything for free (no credit card, runs even when your PC is off)

This project ships a **zero-cost** setup: GitHub runs the scraper on a schedule,
and GitHub Pages hosts the dashboard. Both are free for public repositories,
with no card required. RERA data is public government information, so publishing
it publicly is fine.

## How it works
1. **GitHub Actions** (`.github/workflows/crawl.yml`) runs `run.py` on a daily
   cron — public repos get **unlimited free Actions minutes**.
2. It writes `rera_data.sqlite` and `docs/projects.json`, and commits them back.
3. **GitHub Pages** serves `docs/` — the dashboard (`docs/index.html`) loads
   `projects.json` and does all search/filter/export **in your browser**. No
   server, no database bill.

## One-time setup (about 5 minutes)
1. Create a **free GitHub account** and a new **public** repository.
2. Upload this project's files (or `git push` them).
3. In the repo: **Settings → Pages → Source = "Deploy from a branch",
   Branch = `main`, Folder = `/docs`.** Save.
   Your dashboard goes live at `https://<your-username>.github.io/<repo>/`.
4. In **Settings → Actions → General**, allow "Read and write permissions" so
   the workflow can commit refreshed data.
5. Open the **Actions** tab → run **"RERA crawl"** once (workflow_dispatch) to
   populate data immediately. After that it runs itself daily.

The dashboard already works right now with the 218 real Odisha projects in
`docs/projects.json` — Pages will serve it before the first crawl even runs.

## Other always-free options (if you outgrow the above)
- **Oracle Cloud Always Free** — a genuinely always-free ARM VM (2 vCPU / 12 GB
  as of mid-2026). Enough to run the full FastAPI app + scheduler like a real
  server. Requires a card for identity verification, but isn't charged.
- **Local + Task Scheduler** — run `python run.py` on your own PC on a schedule
  (Windows Task Scheduler / cron). $0, fully private, but only runs when the PC
  is on.

## Limits to know
- Actions schedules pause after 60 days of **repo inactivity** (a commit or
  manual run re-arms it) and can be delayed a few minutes at peak load.
- Pages free tier: 1 GB site, 100 GB bandwidth/month — plenty for this.
- A giant single-state full crawl (Maharashtra ~50k) may approach the 6-hour job
  limit on the first run; incremental daily runs stay small. Split big states
  across separate scheduled jobs if needed.
