from fastapi import APIRouter
import boto3
import os
from datetime import datetime

router = APIRouter(prefix="/api")

DYNAMODB_TABLE = os.environ.get("INCIDENTS_TABLE", "healops-incidents")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DYNAMODB_TABLE)


def humanize_seconds(seconds):
    if seconds is None:
        return "-"
    minutes = seconds // 60
    sec = seconds % 60
    return f"{minutes}m {sec}s"


def fetch_all_incidents():
    response = table.scan()
    items = response.get("Items", [])

    # newest first
    items.sort(
        key=lambda x: x.get("detection_time", ""),
        reverse=True
    )

    return items


@router.get("/dashboard")
def dashboard():
    incidents = fetch_all_incidents()

    resolved = [i for i in incidents if i.get("healing_action")]
    open_incidents = [i for i in incidents if not i.get("healing_action")]

    return {
        "summary": {
            "total_incidents": len(incidents),
            "open_incidents": len(open_incidents),
            "resolved_incidents": len(resolved),
            "avg_mttr_seconds": None,
            "avg_mttr_human": "-"
        },
        "latest": incidents[0] if incidents else None
    }


@router.get("/incidents")
def incidents():
    items = fetch_all_incidents()

    for i in items:
        i["status"] = "RESOLVED" if i.get("healing_action") else "OPEN"
        i["mttr_human"] = "-"
        i["time"] = i.get("detection_time", "undefined")

    return {"items": items}
