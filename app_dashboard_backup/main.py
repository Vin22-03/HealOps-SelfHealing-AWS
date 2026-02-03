from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
import json
from pathlib import Path
from datetime import datetime

APP_DIR = Path(__file__).resolve().parent
DATA_FILE = APP_DIR / "data" / "incidents.json"

app = FastAPI(title="HealOps", version="1.0")

# Static + templates
app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))

def load_incidents():
    if not DATA_FILE.exists():
        return []
    return json.loads(DATA_FILE.read_text())

def compute_summary(incidents):
    total = len(incidents)
    open_count = sum(1 for i in incidents if i.get("status") == "open")
    resolved = [i for i in incidents if i.get("status") == "resolved" and i.get("mttr_seconds") is not None]
    avg_mttr = round(sum(i["mttr_seconds"] for i in resolved) / len(resolved), 2) if resolved else None

    last = incidents[0] if incidents else None
    return {
        "total_incidents": total,
        "open_incidents": open_count,
        "resolved_incidents": total - open_count,
        "avg_mttr_seconds": avg_mttr,
        "last_incident": last,
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/health")
def health():
    return {"status": "healthy", "service": "healops-ui"}

# UI pages
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/incidents", response_class=HTMLResponse)
def incidents_page(request: Request):
    return templates.TemplateResponse("incidents.html", {"request": request})

# JSON APIs
@app.get("/api/incidents")
def api_incidents():
    incidents = load_incidents()
    return {"incidents": incidents}

@app.get("/api/summary")
def api_summary():
    incidents = load_incidents()
    return compute_summary(incidents)
