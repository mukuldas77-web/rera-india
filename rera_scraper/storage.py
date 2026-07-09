"""SQLite store with upsert + diffing so recurring runs surface NEW registrations."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    state TEXT NOT NULL,
    rera_reg_no TEXT NOT NULL,
    project_name TEXT,
    status TEXT, promoter_name TEXT, promoter_address TEXT, promoter_contact TEXT,
    project_type TEXT, district TEXT, locality TEXT, address TEXT, pincode TEXT,
    approved_on TEXT, proposed_completion TEXT, total_units TEXT, total_area_sqm TEXT,
    detail_url TEXT, source_url TEXT, scraped_at TEXT, extra TEXT,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    PRIMARY KEY (state, rera_reg_no)
);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_first_seen ON projects(first_seen);
"""


class Store:
    def __init__(self, db_path="rera_data.sqlite"):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.executescript(SCHEMA)

    def upsert(self, projects) -> dict:
        """Insert/update records. Returns {'new': [...], 'updated': n, 'total': n}."""
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        new_records, updated = [], 0
        cur = self.conn.cursor()
        for p in projects:
            row = p.to_row()
            row["scraped_at"] = row["scraped_at"] or now
            cur.execute(
                "SELECT 1 FROM projects WHERE state=? AND rera_reg_no=?",
                (row["state"], row["rera_reg_no"]),
            )
            exists = cur.fetchone()
            if exists:
                cur.execute(
                    """UPDATE projects SET project_name=:project_name, status=:status,
                       promoter_name=:promoter_name, promoter_address=:promoter_address,
                       promoter_contact=:promoter_contact, project_type=:project_type,
                       district=:district, locality=:locality, address=:address,
                       pincode=:pincode, approved_on=:approved_on,
                       proposed_completion=:proposed_completion, total_units=:total_units,
                       total_area_sqm=:total_area_sqm, detail_url=:detail_url,
                       source_url=:source_url, scraped_at=:scraped_at, extra=:extra,
                       last_seen=:now
                       WHERE state=:state AND rera_reg_no=:rera_reg_no""",
                    {**row, "now": now},
                )
                updated += 1
            else:
                cur.execute(
                    """INSERT INTO projects VALUES (:state,:rera_reg_no,:project_name,
                       :status,:promoter_name,:promoter_address,:promoter_contact,
                       :project_type,:district,:locality,:address,:pincode,:approved_on,
                       :proposed_completion,:total_units,:total_area_sqm,:detail_url,
                       :source_url,:scraped_at,:extra,:now,:now)""",
                    {**row, "now": now},
                )
                new_records.append(row)
        self.conn.commit()
        total = cur.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        return {"new": new_records, "updated": updated, "total": total}

    def export(self, path="rera_projects.xlsx", states=None):
        q = "SELECT * FROM projects"
        params = ()
        if states:
            q += f" WHERE state IN ({','.join('?' * len(states))})"
            params = tuple(states)
        df = pd.read_sql_query(q, self.conn, params=params)
        path = Path(path)
        if path.suffix == ".csv":
            df.to_csv(path, index=False)
        else:
            # one sheet per state + combined
            with pd.ExcelWriter(path, engine="openpyxl") as xw:
                df.to_excel(xw, sheet_name="ALL", index=False)
                for state, g in df.groupby("state"):
                    g.to_excel(xw, sheet_name=state[:31], index=False)
        return path, len(df)

    def new_since(self, iso_date: str):
        df = pd.read_sql_query(
            "SELECT * FROM projects WHERE first_seen >= ? ORDER BY first_seen DESC",
            self.conn, params=(iso_date,),
        )
        return df
