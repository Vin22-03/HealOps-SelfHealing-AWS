
from fastapi import APIRouter
import boto3
import os
from decimal import Decimal

router = APIRouter(prefix="/api")

# -----------------------------------
# DynamoDB
# -----------------------------------
INCIDENTS_TABLE = os.environ.get("INCIDENTS_TABLE", "healops-incidents")


def get_dynamodb_table():
    """
    IMPORTANT:
    - Do NOT force AWS_REGION
    - In ECS, boto3 auto-detects region via task metadata
    """
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(INCIDENTS_TABLE)


# -----------------------------------
# Helpers
# -----------------------------------
def decimal_safe(v):
    if isinstance(v, Decimal):
        return int(v) if v % 1 == 0 else float(v)
    return v


def json_safe_item(item: dict):
    safe = {}
    for k, v in item.items():
        safe[k] = decimal_safe(v)
    return safe


def humanize_seconds(seconds):
    if seconds is None:
        return "—"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    return f"{seconds // 60}m {seconds % 60}s"


# -----------------------------------
# Formatting (UI = DynamoDB mirror)
# -----------------------------------
def format_incident(item: dict):
    return {
        # identity
        "service": item.get("service"),
        "incident_type": item.get("incident_type") or item.get("failure_type"),
        "failure_type": item.get("failure_type"),
        "failure_reason": item.get("failure_reason"),  #  FIX ADDED 
        # timing
        "failure_time": item.get("detection_time"),
        "healed_time": item.get("healed_time"),
        "mttr_seconds": item.get("mttr_seconds"),
        "mttr_human": humanize_seconds(item.get("mttr_seconds")),

        # detection & healing
        "component": item.get("component", "ECS"),
        "detection": item.get("detected_by"),
        "healing_action": item.get("healing_action"),
        "status": item.get("status", "OPEN"),

        # autoscaling evidence (CRITICAL)
        "desired_before": item.get("desired_before"),
        "desired_after": item.get("desired_after"),
        "running_before": item.get("running_before"),
        "running_after": item.get("running_after"),
        "pending_before": item.get("pending_before"),
        "pending_after": item.get("pending_after"),
        "scale_delta": item.get("scale_delta"),
        "alarm_name": item.get("alarm_name"),

        # metadata
        "cluster": item.get("cluster"),
        "region": item.get("region"),
        "exit_code": item.get("exit_code"),
        "task_arn": item.get("task_arn"),
        "task_last_status": item.get("task_last_status"),
        "task_desired_status": item.get("task_desired_status"),
        "source_event_id": item.get("source_event_id"),
    }


# -----------------------------------
# Data fetch
# -----------------------------------
def fetch_all_incidents():
    table = get_dynamodb_table()

    items = []
    resp = table.scan()
    items.extend(resp.get("Items", []))

    while "LastEvaluatedKey" in resp:
        resp = table.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
        items.extend(resp.get("Items", []))

    # JSON-safe first
    items = [json_safe_item(i) for i in items]

    # newest first
    items.sort(key=lambda x: x.get("detection_time", ""), reverse=True)
    return items


# -----------------------------------
# API: Dashboard
# -----------------------------------
@router.get("/dashboard")
def dashboard():
    raw = fetch_all_incidents()
    items = [format_incident(i) for i in raw]

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


# -----------------------------------
# API: Incidents (UI SOURCE OF TRUTH)
# -----------------------------------
@router.get("/incidents")
def incidents():
    raw = fetch_all_incidents()
    items = [format_incident(i) for i in raw]
    return {"items": items}
