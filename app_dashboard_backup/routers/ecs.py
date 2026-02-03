from fastapi import APIRouter
from app.core.state import INCIDENTS, SIM, create_incident, resolve_incident, calc_mttr

router = APIRouter()

@router.get("/")
def list_incidents():
    return {
        "incidents": [i.to_dict() for i in INCIDENTS],
        "mttr_seconds_avg": calc_mttr(),
        "simulation": SIM
    }

@router.post("/break/health")
def break_health():
    SIM["health_fail"] = True
    inc = create_incident(
        title="Health check failing",
        severity="P1",
        signal="health_check_failed",
        action="ecs_replace_task",
        notes="Simulated /health returns 500. In AWS, ALB marks target unhealthy; ECS replaces task."
    )
    return {"ok": True, "incident": inc.to_dict(), "simulation": SIM}

@router.post("/break/latency/{ms}")
def break_latency(ms: int):
    SIM["latency_ms"] = max(0, min(ms, 5000))
    inc = create_incident(
        title=f"Latency injected: {SIM['latency_ms']}ms",
        severity="P2",
        signal="latency_spike",
        action="scale_out",
        notes="Simulated latency. In AWS, alarm triggers scaling; SRE checks upstream/downstream."
    )
    return {"ok": True, "incident": inc.to_dict(), "simulation": SIM}

@router.post("/fix/health")
def fix_health():
    SIM["health_fail"] = False
    SIM["latency_ms"] = 0

    # Resolve latest open incident (simple demo)
    open_ids = [i.id for i in INCIDENTS if i.status == "open"]
    resolved = resolve_incident(open_ids[0]) if open_ids else None

    return {
        "ok": True,
        "resolved": resolved.to_dict() if resolved else None,
        "mttr_seconds_avg": calc_mttr(),
        "simulation": SIM
    }

@router.post("/resolve/{incident_id}")
def resolve_by_id(incident_id: str):
    resolved = resolve_incident(incident_id)
    return {"ok": bool(resolved), "resolved": resolved.to_dict() if resolved else None, "mttr_seconds_avg": calc_mttr()}
