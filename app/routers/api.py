from fastapi import APIRouter
import boto3
import os

router = APIRouter(prefix="/api")

# -----------------------------
# DynamoDB (LAZY INIT)
# -----------------------------
DYNAMODB_TABLE = os.environ.get("INCIDENTS_TABLE", "healops-incidents")


def get_dynamodb_table():
    # In ECS/Fargate you MUST have region in env OR default config
    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
    if not region:
        raise RuntimeError("AWS region not set (set AWS_REGION in ECS task env)")

    dynamodb = boto3.resource("dynamodb", region_name=region)
    return dynamodb.Table(DYNAMODB_TABLE)


# -----------------------------
# Helpers
# -----------------------------
def humanize_seconds(seconds: int | None):
    if seconds is None:
        return "—"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    m = seconds // 60
    s = seconds % 60
    return f"{m}m {s}s"


def format_incident(item: dict):
    return {
        "failure_time": item.get("detection_time"),
        "component": item.get("component", "ECS"),
        "failure": item.get("failure_type") or item.get("incident_type"),
        "failure_type": item.get("failure_type"),
        "detection": item.get("detected_by"),
        "healing_action": item.get("healing_action"),
        "mttr_human": humanize_seconds(item.get("mttr_seconds")),
        "mttr_seconds": item.get("mttr_seconds"),
        "status": item.get("status", "OPEN"),
        "healed_time": item.get("healed_time"),
        "cluster": item.get("cluster"),
        "exit_code": item.get("exit_code"),
        "source_event_id": item.get("source_event_id"),
    }


def fetch_all_incidents():
    table = get_dynamodb_table()

    items = []
    resp = table.scan()
    items.extend(resp.get("Items", []))

    # handle pagination
    while "LastEvaluatedKey" in resp:
        resp = table.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
        items.extend(resp.get("Items", []))

    items.sort(key=lambda x: x.get("detection_time", ""), reverse=True)
    return items


# -----------------------------
# API: Dashboard
# -----------------------------
@router.get("/dashboard")
def dashboard():
    raw_items = fetch_all_incidents()
    items = [format_incident(i) for i in raw_items]

    total = len(items)
    open_items = [i for i in items if i["status"] == "OPEN"]
    resolved_items = [i for i in items if i["status"] == "RESOLVED"]

    mttrs = [i["mttr_seconds"] for i in items if i["mttr_seconds"] is not None]
    avg_mttr_seconds = int(sum(mttrs) / len(mttrs)) if mttrs else None

    return {
        "summary": {
            "total_incidents": total,
            "open_incidents": len(open_items),
            "resolved_incidents": len(resolved_items),
            "avg_mttr_seconds": avg_mttr_seconds,
            "avg_mttr_human": humanize_seconds(avg_mttr_seconds),
        },
        "latest": items[0] if items else None,
    }


# -----------------------------
# API: Incidents
# -----------------------------
@router.get("/incidents")
def incidents():
    raw_items = fetch_all_incidents()
    items = [format_incident(i) for i in raw_items]
    return {"items": items}
