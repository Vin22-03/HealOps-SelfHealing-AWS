import os
import json
import logging
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key

# -----------------------------
# Logging
# -----------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger("healops-incident-ingestor")

# -----------------------------
# DynamoDB
# -----------------------------
DYNAMODB_TABLE = os.getenv("INCIDENTS_TABLE", "healops-incidents")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DYNAMODB_TABLE)

DEFAULT_SERVICE_NAME = os.getenv("SERVICE_NAME", "healops-service")

# -----------------------------
# AWS clients
# -----------------------------
ecs = boto3.client("ecs")

# -----------------------------
# Helpers
# -----------------------------
def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def seconds_between(start, end):
    try:
        s = datetime.fromisoformat(start.replace("Z", "+00:00"))
        e = datetime.fromisoformat(end.replace("Z", "+00:00"))
        return int((e - s).total_seconds())
    except Exception:
        return None


def put_open(item):
    item["status"] = "OPEN"
    item["healed_time"] = None
    item["mttr_seconds"] = None
    table.put_item(Item=item)


def find_open(service, incident_type):
    resp = table.query(
        KeyConditionExpression=Key("service").eq(service),
        ScanIndexForward=False,
        Limit=10,
    )
    for it in resp.get("Items", []):
        if it["status"] == "OPEN" and it["incident_type"] == incident_type:
            return it
    return None


def resolve(service, incident_type, healed_time, healing_action):
    item = find_open(service, incident_type)
    if not item:
        return

    mttr = seconds_between(item["detection_time"], healed_time)

    table.update_item(
        Key={
            "service": service,
            "detection_time": item["detection_time"]
        },
        UpdateExpression="""
            SET #s=:r,
                healed_time=:h,
                mttr_seconds=:m,
                healing_action=:ha
        """,
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":r": "RESOLVED",
            ":h": healed_time,
            ":m": mttr,
            ":ha": healing_action,
        }
    )


def ecs_service_healthy(cluster, service):
    resp = ecs.describe_services(cluster=cluster, services=[service])
    s = resp["services"][0]
    return s["runningCount"] == s["desiredCount"]


# =========================================================
# 1️⃣ ECS TASK STOPPED (OPEN) + SELF HEAL (RESOLVE)
# =========================================================
def handle_ecs_task_state_change(event):
    detail = event["detail"]

    if detail["lastStatus"] != "STOPPED":
        return {"ignored": True}

    cluster = detail["clusterArn"].split("/")[-1]
    group = detail.get("group", "")
    service = group.split("service:")[-1] if "service:" in group else DEFAULT_SERVICE_NAME

    detection_time = event["time"]

    put_open({
        "service": service,
        "detection_time": detection_time,
        "cluster": cluster,
        "component": "ECS",
        "incident_type": "TASK_STOPPED",
        "failure_reason": detail.get("stoppedReason", "Task stopped"),
        "detected_by": "EventBridge",
        "healing_action": "ECS_SCHEDULER_RESTART"
    })

    # ✅ resolve ONLY when ECS is actually healthy
    if ecs_service_healthy(cluster, service):
        resolve(
            service,
            "TASK_STOPPED",
            utc_now(),
            "ECS_SERVICE_RESTORED"
        )

    return {"task": "handled"}


# =========================================================
# 2️⃣ CPU SPIKE (CloudWatch Alarm) — CORRECT WAY
# =========================================================
def handle_cloudwatch_alarm(event):
    detail = event["detail"]
    state = detail["state"]["value"]
    alarm = detail["alarmName"]
    service = DEFAULT_SERVICE_NAME
    now = event["time"]

    if state == "ALARM":
        put_open({
            "service": service,
            "detection_time": now,
            "component": "ECS",
            "incident_type": "CPU_HIGH",
            "failure_reason": f"Alarm {alarm} entered ALARM",
            "detected_by": "CloudWatch",
            "healing_action": "ECS_AUTOSCALING"
        })
        return {"cpu": "open"}

    if state == "OK":
        resolve(
            service,
            "CPU_HIGH",
            now,
            "CPU_NORMALIZED"
        )
        return {"cpu": "resolved"}

    return {"cpu": "ignored"}


# =========================================================
# Lambda entry
# =========================================================
def lambda_handler(event, context):
    logger.info(json.dumps(event))

    dtype = event.get("detail-type")

    if dtype == "ECS Task State Change":
        return handle_ecs_task_state_change(event)

    if dtype == "CloudWatch Alarm State Change":
        return handle_cloudwatch_alarm(event)

    return {"ignored": dtype}


def handler(event, context):
    return lambda_handler(event, context)
