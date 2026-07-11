"""Web app for the universal Scrapling scraper.

Paste any listing URL -> scrape -> view + download. Runs the UniversalScraper
engine behind a small FastAPI UI.

Run locally (needs the scraper deps + browsers):
    pip install --user fastapi "uvicorn[standard]" pandas openpyxl beautifulsoup4 "scrapling[fetchers]"
    python -m playwright install chromium
    python -m uvicorn webapp.scraper_app:app --port 8010   # from the repo root
"""
import io
import sys
from pathlib import Path

import pandas as pd
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rera_scraper.universal import UniversalScraper  # noqa: E402

app = FastAPI(title="Universal Scraper")
_last = {"rows": []}


class Req(BaseModel):
    url: str
    mode: str = "auto"
    engine: str = "auto"
    stealth: bool = False
    pages: int = 50
    resolve_coords: bool = False


@app.post("/api/scrape")
def scrape(req: Req):
    try:
        rows = UniversalScraper(req.url, mode=req.mode, engine=req.engine,
                                stealth=req.stealth, max_pages=req.pages,
                                resolve_coords=req.resolve_coords).scrape()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    _last["rows"] = rows
    cols = list({k for r in rows for k in r})
    return {"count": len(rows), "columns": cols, "rows": rows[:500]}


@app.get("/api/download")
def download():
    rows = _last["rows"]
    df = pd.DataFrame(rows if rows else [{"info": "no data"}])
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        df.to_excel(xw, index=False, sheet_name="scraped")
    buf.seek(0)
    return StreamingResponse(
        buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=scraped.xlsx"})


@app.get("/api/download.csv")
def download_csv():
    rows = _last["rows"]
    df = pd.DataFrame(rows if rows else [{"info": "no data"}])
    csv_text = df.to_csv(index=False)
    return StreamingResponse(
        io.BytesIO(csv_text.encode("utf-8-sig")), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=scraped.csv"})


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML


HTML = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Universal Scraper</title>
<style>
 :root{--bg:#0f172a;--card:#1e293b;--ink:#e2e8f0;--mut:#94a3b8;--acc:#38bdf8;--line:#334155}
 *{box-sizing:border-box}body{margin:0;font:14px system-ui,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--ink)}
 header{padding:18px 24px;border-bottom:1px solid var(--line)}h1{font-size:18px;margin:0}
 .wrap{padding:20px 24px;max-width:1200px;margin:0 auto}
 .row{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:12px}
 input,select,button{background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:10px 12px;font:inherit}
 input#url{flex:1;min-width:320px}
 button{cursor:pointer;background:var(--acc);color:#04263a;border:0;font-weight:700}
 button.ghost{background:var(--card);color:var(--ink);border:1px solid var(--line)}
 table{width:100%;border-collapse:collapse;background:var(--card);border-radius:10px;overflow:hidden;margin-top:14px;font-size:13px}
 th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);white-space:nowrap;max-width:320px;overflow:hidden;text-overflow:ellipsis}
 th{color:var(--mut);position:sticky;top:0;background:#243247}
 .mut{color:var(--mut)}.err{color:#f87171}
</style></head><body>
<header><h1>Universal Scraper - paste a URL, get a table</h1></header>
<div class="wrap">
 <div class="row">
   <input id="url" placeholder="https://any-site/list  (use {page} where the page number goes)">
   <select id="engine"><option value="auto">auto engine</option><option value="static">static (fast)</option><option value="dynamic">dynamic (browser)</option></select>
   <select id="mode"><option value="auto">auto mode</option><option value="single">single page</option><option value="paged">paged</option></select>
   <label class="mut"><input type="checkbox" id="stealth"> anti-bot</label>
   <label class="mut" title="follow each location link and read exact lat/long (slower)"><input type="checkbox" id="coords"> get lat/long</label>
   <input id="pages" type="number" value="50" style="width:90px" title="max pages">
   <button onclick="run()">Scrape</button>
   <button class="ghost" id="csvbtn" onclick="dlcsv()" disabled>Download CSV</button>
   <button class="ghost" id="xlsxbtn" onclick="dl()" disabled>Download .xlsx</button>
 </div>
 <div id="status" class="mut">Enter a listing URL and click Scrape. JS-heavy sites: choose "dynamic". Tick "get lat/long" for coordinates.</div>
 <div id="out"></div>
</div>
<script>
const $=id=>document.getElementById(id);
async function run(){
 $('status').textContent='Scraping... (this can take a while for many pages / coordinates)';
 $('out').innerHTML='';
 document.getElementById('csvbtn').disabled=true; document.getElementById('xlsxbtn').disabled=true;
 try{
  const r=await fetch('/api/scrape',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({url:$('url').value,mode:$('mode').value,engine:$('engine').value,
      stealth:$('stealth').checked,pages:parseInt($('pages').value)||50,resolve_coords:$('coords').checked})});
  const d=await r.json();
  if(d.error){$('status').innerHTML='<span class="err">Error: '+d.error+'</span>';return;}
  $('status').innerHTML='<b style="color:#6ee7b7">✓ Scraping done</b> — '+d.count+' rows'+(d.count>500?' (showing first 500; full set is in the download)':'');
  document.getElementById('csvbtn').disabled=false; document.getElementById('xlsxbtn').disabled=false;
  if(!d.rows.length){$('out').innerHTML='<p class="mut">No rows found. Try engine=dynamic or check the URL.</p>';return;}
  const cols=d.columns;
  let h='<table><thead><tr>'+cols.map(c=>'<th>'+c+'</th>').join('')+'</tr></thead><tbody>';
  h+=d.rows.map(r=>'<tr>'+cols.map(c=>'<td>'+((r[c]??'')+'').replace(/</g,'&lt;')+'</td>').join('')+'</tr>').join('');
  $('out').innerHTML=h+'</tbody></table>';
 }catch(e){$('status').innerHTML='<span class="err">'+e+'</span>';}
}
function dl(){window.location='/api/download';}
function dlcsv(){window.location='/api/download.csv';}
$('url').addEventListener('keydown',e=>{if(e.key==='Enter')run();});
</script></body></html>"""
