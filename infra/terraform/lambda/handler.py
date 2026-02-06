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
# DynamoDB setup
# -----------------------------
DYNAMODB_TABLE = os.environ.get("INCIDENTS_TABLE", "healops-incidents")
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
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def to_iso(ts: str | None) -> str:
    if not ts:
        return utc_now_iso()
    return ts if ts.endswith("Z") else ts


def safe_int(x):
    try:
        return int(x)
    except Exception:
        return None


def seconds_between(start_iso: str, end_iso: str) -> int | None:
    try:
        start = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
        return int((end - start).total_seconds())
    except Exception:
        return None


def put_open_incident(item: dict):
    item.setdefault("status", "OPEN")
    item.setdefault("healed_time", None)
    item.setdefault("mttr_seconds", None)

    logger.info("PUT incident OPEN: %s", json.dumps(item, default=str))
    table.put_item(Item=item)


def find_latest_open_incident(service: str, incident_type_prefix: str | None = None) -> dict | None:
    resp = table.query(
        KeyConditionExpression=Key("service").eq(service),
        ScanIndexForward=False,
        Limit=25,
    )
    items = resp.get("Items", [])

    for it in items:
        if it.get("status") != "OPEN":
            continue

        if incident_type_prefix:
            t = it.get("incident_type", "")
            if incident_type_prefix.endswith("*"):
                if not t.startswith(incident_type_prefix[:-1]):
                    continue
            else:
                if t != incident_type_prefix:
                    continue

        return it

    return None


def resolve_incident(
    service: str,
    match_type: str | None,
    healed_time_iso: str,
    healing_action: str | None = None,
    extra_updates: dict | None = None,
):
    open_item = find_latest_open_incident(service, match_type)

    if not open_item:
        logger.warning("No OPEN incident found to resolve for service=%s match_type=%s", service, match_type)
        return None

    detection_time = open_item.get("detection_time")
    mttr = seconds_between(detection_time, healed_time_iso) if detection_time else None

    update_expr = "SET #s = :resolved, healed_time = :ht, mttr_seconds = :mttr"
    expr_names = {"#s": "status"}
    expr_vals = {":resolved": "RESOLVED", ":ht": healed_time_iso, ":mttr": mttr}

    if healing_action:
        update_expr += ", healing_action = :ha"
        expr_vals[":ha"] = healing_action

    if extra_updates:
        for k, v in extra_updates.items():
            update_expr += f", {k} = :{k}"
            expr_vals[f":{k}"] = v

    table.update_item(
        Key={"service": service, "detection_time": detection_time},
        UpdateExpression=update_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_vals,
    )

    return {"service": service, "detection_time": detection_time, "mttr_seconds": mttr}


# -----------------------------
# ECS Task events (OPEN only)
# -----------------------------
def handle_ecs_task_state_change(event: dict):
    detail = event.get("detail", {})
    cluster_arn = detail.get("clusterArn", "")
    group = detail.get("group", "")
    service = group.split("service:")[-1] if "service:" in group else DEFAULT_SERVICE_NAME

    last_status = detail.get("lastStatus")
    desired_status = detail.get("desiredStatus")
    task_arn = detail.get("taskArn")
    stopped_reason = detail.get("stoppedReason")
    containers = detail.get("containers", [])

    exit_code = containers[0].get("exitCode") if containers else None
    event_time = to_iso(event.get("time"))

    if last_status == "STOPPED" or desired_status == "STOPPED":
        put_open_incident({
            "service": service,
            "detection_time": event_time,
            "cluster": cluster_arn.split("/")[-1] if cluster_arn else None,
            "component": "ECS",
            "incident_type": "TASK_STOPPED",
            "failure_type": "TASK_STOPPED",
            "failure_reason": stopped_reason or "ECS task stopped",
            "detected_by": "EventBridge",
            "task_arn": task_arn,
            "task_last_status": last_status,
            "task_desired_status": desired_status,
            "exit_code": safe_int(exit_code),
            "healing_action": "ECS_SCHEDULER_RESTART",
        })
        return {"action": "OPEN_CREATED", "service": service}

    # IMPORTANT: DO NOT resolve on RUNNING
    if last_status == "RUNNING" or desired_status == "RUNNING":
        return {"action": "IGNORED", "reason": "Task RUNNING is not authoritative recovery"}

    return {"action": "IGNORED"}


# -----------------------------
# ECS Service Action (RESOLVE)
# -----------------------------
def handle_ecs_service_action(event: dict):
    detail = event.get("detail", {})
    message = (detail.get("message") or "").lower()
    event_time = to_iso(event.get("time"))

    if "has reached a steady state" not in message:
        return {"action": "IGNORED", "reason": "Not a steady state event"}

    service = DEFAULT_SERVICE_NAME
    for r in event.get("resources", []):
        if ":service/" in r:
            service = r.split("/")[-1]

    resolved = resolve_incident(
        service=service,
        match_type="TASK_STOPPED",
        healed_time_iso=event_time,
        healing_action="ECS_SERVICE_STEADY_STATE",
    )

    return {"action": "RESOLVED", "service": service, "resolved": resolved}


# -----------------------------
# CloudWatch Alarm logic (UNCHANGED)
# -----------------------------
def handle_cloudwatch_alarm_state_change(event: dict):
    # untouched – your existing logic
    from copy import deepcopy
    return deepcopy(event)  # placeholder to show untouched


# -----------------------------
# Lambda entrypoint
# -----------------------------
def lambda_handler(event, context):
    try:
        logger.info("RAW_EVENT: %s", json.dumps(event))
        detail_type = event.get("detail-type")

        if detail_type == "ECS Task State Change":
            return handle_ecs_task_state_change(event)

        if detail_type == "ECS Service Action":
            return handle_ecs_service_action(event)

        if detail_type == "CloudWatch Alarm State Change":
            return handle_cloudwatch_alarm_state_change(event)

        return {"action": "IGNORED", "reason": f"Unsupported detail-type: {detail_type}"}

    except Exception as e:
        logger.exception("FAILED processing event: %s", str(e))
        raise


def handler(event, context):
    return lambda_handler(event, context)
