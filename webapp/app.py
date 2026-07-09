"""RERA India — web dashboard + API over the scraped project database.

Run locally:   uvicorn webapp.app:app --reload --port 8000   (from repo root)
Then open:     http://localhost:8000
"""
import io
import os
import sqlite3
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse

DB = os.environ.get("RERA_DB", str(Path(__file__).resolve().parent.parent / "rera_data.sqlite"))

app = FastAPI(title="RERA India Dashboard", version="1.0")


def q(sql, params=()):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in con.execute(sql, params).fetchall()]
    finally:
        con.close()


def _where(state, district, promoter, status, search, since):
    clauses, params = [], []
    if state:    clauses.append("state = ?");                         params.append(state)
    if district: clauses.append("district = ?");                      params.append(district)
    if promoter: clauses.append("promoter_name LIKE ?");              params.append(f"%{promoter}%")
    if status:   clauses.append("status = ?");                        params.append(status)
    if since:    clauses.append("first_seen >= ?");                   params.append(since)
    if search:
        clauses.append("(project_name LIKE ? OR promoter_name LIKE ? OR rera_reg_no LIKE ?)")
        params += [f"%{search}%"] * 3
    return (" WHERE " + " AND ".join(clauses) if clauses else ""), params


@app.get("/api/stats")
def stats():
    total = q("SELECT COUNT(*) n FROM projects")[0]["n"]
    by_state = q("SELECT state, COUNT(*) n FROM projects GROUP BY state ORDER BY n DESC")
    by_status = q("SELECT status, COUNT(*) n FROM projects GROUP BY status ORDER BY n DESC")
    newest = q("SELECT MAX(first_seen) m FROM projects")[0]["m"]
    return {"total": total, "by_state": by_state, "by_status": by_status, "latest_ingest": newest}


@app.get("/api/filters")
def filters():
    return {
        "states": [r["state"] for r in q("SELECT DISTINCT state FROM projects ORDER BY state")],
        "districts": [r["district"] for r in q(
            "SELECT DISTINCT district FROM projects WHERE district<>'' ORDER BY district")],
        "statuses": [r["status"] for r in q("SELECT DISTINCT status FROM projects ORDER BY status")],
    }


@app.get("/api/projects")
def projects(state: str = "", district: str = "", promoter: str = "", status: str = "",
             search: str = "", since: str = "", limit: int = Query(100, le=1000), offset: int = 0):
    where, params = _where(state, district, promoter, status, search, since)
    total = q(f"SELECT COUNT(*) n FROM projects{where}", params)[0]["n"]
    rows = q(f"""SELECT state, rera_reg_no, project_name, promoter_name, district,
                 project_type, status, approved_on, total_units, first_seen
                 FROM projects{where} ORDER BY first_seen DESC, rera_reg_no DESC
                 LIMIT ? OFFSET ?""", params + [limit, offset])
    return {"total": total, "count": len(rows), "results": rows}


@app.get("/api/export")
def export(state: str = "", district: str = "", promoter: str = "", status: str = "",
           search: str = "", since: str = ""):
    where, params = _where(state, district, promoter, status, search, since)
    df = pd.DataFrame(q(f"SELECT * FROM projects{where} ORDER BY state, rera_reg_no", params))
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        (df if len(df) else pd.DataFrame([{"info": "no rows"}])).to_excel(xw, index=False, sheet_name="RERA")
    buf.seek(0)
    return StreamingResponse(
        buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=rera_export.xlsx"})


@app.get("/", response_class=HTMLResponse)
def index():
    return (Path(__file__).resolve().parent / "static" / "index.html").read_text(encoding="utf-8")
