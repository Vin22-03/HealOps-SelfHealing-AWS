from fastapi import APIRouter
from datetime import datetime
import uuid

router = APIRouter(prefix="/api/incidents", tags=["incidents"])

INCIDENTS = []

@router.get("/")
def list_incidents():
    resolved = [i for i in INCIDENTS if i["status"] == "resolved"]
    mttrs = [
        (i["resolved_at"] - i["created_at"]).total_seconds()
        for i in resolved
    ]
    avg_mttr = round(sum(mttrs) / len(mttrs), 2) if mttrs else None

    return {
        "incidents": INCIDENTS[-8:][::-1],
        "mttr": avg_mttr
    }

@router.post("/break/{severity}")
def break_system(severity: str):
    incident = {
        "id": str(uuid.uuid4())[:8],
        "title": "Health Check Failure" if severity == "p1" else "Latency Spike",
        "severity": severity.upper(),
        "status": "open",
        "created_at": datetime.utcnow(),
        "resolved_at": None
    }
    INCIDENTS.append(incident)
    return {"message": "incident created", "incident": incident}

@router.post("/resolve")
def resolve_latest():
    for i in reversed(INCIDENTS):
        if i["status"] == "open":
            i["status"] = "resolved"
            i["resolved_at"] = datetime.utcnow()
            return {"message": "incident resolved", "incident": i}
    return {"message": "no open incidents"}
