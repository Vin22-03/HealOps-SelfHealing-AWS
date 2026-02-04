from fastapi import APIRouter
import boto3
import os
from datetime import datetime

router = APIRouter(prefix="/api")

# -----------------------------
# DynamoDB setup
# -----------------------------
DYNAMODB_TABLE = os.environ.get("INCIDENTS_TABLE", "healops-incidents")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DYNAMODB_TABLE)


# -----------------------------
# Helpers
# -----------------------------
def humanize_seconds(seconds: int) -> str:
    if seconds is None:
        return "-"
    minutes = seconds // 60
    sec = seconds % 60
    return f"{minutes}m {sec}s"


def fetch_all_incidents():
    """
    Scan is acceptable here because:
    - Demo / single service
    - Small dataset
    - Simple & predictable
    """
    response = table.scan()
    items = response.get("Items", [])

    # Sort newest first
    items.sort(
        key=lambda x: x.get("detection_time", ""),
        reverse=True
    )

    return items


# -----------------------------
# Dashboard API
# -----------------------------
@router.get("/dashboard")
def dashboard():
    incidents = fetch_all_incidents()

    total = len(incidents)
    resolved = [i for i in incidents if i.get("status") == "RESOLVED"]
    open_incidents = [i for i in incidents if i.get("status") == "OPEN"]

    mttr_values = [
        i.get("mttr_seconds") for i in resolved
        if i.get("mttr_seconds") is not None
    ]

    avg_mttr = int(sum(mttr_values) / len(mttr_values)) if mttr_values else None

    latest = incidents[0] if incidents else None

    return {
        "summary": {
            "total_incidents": total,
            "open_incidents": len(open_incidents),
            "resolved_incidents": len(resolved),
            "avg_mttr_seconds": avg_mttr,
            "avg_mttr_human": humanize_seconds(avg_mttr)
        },
        "latest": latest
    }


# -----------------------------
# Incidents API
# -----------------------------
@router.get("/incidents")
def incidents():
    items = fetch_all_incidents()

    for i in items:
        i["mttr_human"] = humanize_seconds(i.get("mttr_seconds"))

    return {
        "items": items
    }
