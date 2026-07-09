"""Dump the SQLite DB to docs/projects.json for the static (GitHub Pages) site.
Run after scraping:  python export_json.py
"""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB = "rera_data.sqlite"
OUT = Path("docs/projects.json")

def main():
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(
        """SELECT state, rera_reg_no, project_name, promoter_name, district,
           project_type, status, approved_on, total_units, first_seen
           FROM projects ORDER BY first_seen DESC, rera_reg_no DESC""")]
    states = {}
    for r in rows:
        states[r["state"]] = states.get(r["state"], 0) + 1
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total": len(rows),
        "by_state": states,
        "projects": rows,
    }, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT} — {len(rows)} projects across {len(states)} states")

if __name__ == "__main__":
    main()
