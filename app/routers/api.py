import json
from pathlib import Path
from datetime import datetime, timezone
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["api"])

DATA_PATH = Path("app/data/incidents.json")

def _parse_iso(ts: str) -> datetime:
    # Expect ISO like "2026-02-03T14:01:00Z"
    if ts.endswith("Z"):
        ts = ts.replace("Z", "+00:00")
    return datetime.fromisoformat(ts)

def _fmt_seconds(secs: int) -> str:
    if secs < 60:
        return f"{secs}s"
    m, s = divmod(secs, 60)
    if m < 60:
        return f"{m}m {s}s"
    h, rem = divmod(m, 60)
    return f"{h}h {rem}m"

def load_incidents():
    if not DATA_PATH.exists():
        return []

    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    incidents = []
    for inc in raw:
        failure = _parse_iso(inc["failure_time"])
        recovery = _parse_iso(inc["recovery_time"]) if inc.get("recovery_time") else None

        mttr_seconds = None
        if recovery:
            mttr_seconds = int((recovery - failure).total_seconds())

        inc["mttr_seconds"] = mttr_seconds
        inc["mttr_human"] = _fmt_seconds(mttr_seconds) if mttr_seconds is not None else "—"
        inc["failure_hm"] = failure.astimezone(timezone.utc).strftime("%H:%M UTC")
        inc["recovery_hm"] = recovery.astimezone(timezone.utc).strftime("%H:%M UTC") if recovery else "—"
        incidents.append(inc)

    # latest first
    incidents.sort(key=lambda x: x["failure_time"], reverse=True)
    return incidents

@router.get("/incidents")
def get_incidents():
    return {"items": load_incidents()}

@router.get("/dashboard")
def get_dashboard():
    items = load_incidents()
    total = len(items)
    open_count = sum(1 for i in items if i.get("status") == "OPEN")
    resolved_count = sum(1 for i in items if i.get("status") == "RESOLVED")

    mttrs = [i["mttr_seconds"] for i in items if i.get("mttr_seconds") is not None]
    avg_mttr = int(sum(mttrs) / len(mttrs)) if mttrs else None

    latest = items[:6]

    return {
        "summary": {
            "total_incidents": total,
            "open": open_count,
            "resolved": resolved_count,
            "avg_mttr_seconds": avg_mttr,
        },
        "latest": latest
    }
