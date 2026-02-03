from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional, List
import uuid

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

@dataclass
class Incident:
    id: str
    title: str
    severity: str            # P1/P2/P3
    signal: str              # health_check_failed, task_stopped, deploy_failed, cpu_spike
    action: str              # ecs_replace_task, rollback, scale_out, manual_fix
    status: str              # open/resolved
    failure_time: datetime
    recovery_time: Optional[datetime] = None
    notes: str = ""

    def mttr_seconds(self) -> Optional[int]:
        if self.recovery_time is None:
            return None
        return int((self.recovery_time - self.failure_time).total_seconds())

    def to_dict(self):
        d = asdict(self)
        d["failure_time"] = self.failure_time.isoformat()
        d["recovery_time"] = self.recovery_time.isoformat() if self.recovery_time else None
        d["mttr_seconds"] = self.mttr_seconds()
        return d

# --- In-memory state (good for demo; later DynamoDB) ---
INCIDENTS: List[Incident] = []

# Simulation flags (used by /health + UI)
SIM = {
    "health_fail": False,
    "latency_ms": 0,
    "last_signal": "none",
    "last_action": "none",
}

def create_incident(title: str, severity: str, signal: str, action: str, notes: str = "") -> Incident:
    inc = Incident(
        id=str(uuid.uuid4())[:8],
        title=title,
        severity=severity,
        signal=signal,
        action=action,
        status="open",
        failure_time=now_utc(),
        notes=notes,
    )
    INCIDENTS.insert(0, inc)
    SIM["last_signal"] = signal
    SIM["last_action"] = action
    return inc

def resolve_incident(incident_id: str) -> Optional[Incident]:
    for inc in INCIDENTS:
        if inc.id == incident_id and inc.status == "open":
            inc.status = "resolved"
            inc.recovery_time = now_utc()
            return inc
    return None

def calc_mttr() -> Optional[int]:
    resolved = [i for i in INCIDENTS if i.status == "resolved" and i.mttr_seconds() is not None]
    if not resolved:
        return None
    return int(sum(i.mttr_seconds() for i in resolved) / len(resolved))
