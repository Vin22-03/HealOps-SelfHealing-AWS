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


# -----------------------------
# Helpers
# -----------------------------
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def to_iso(ts: str | None) -> str:
    """
    EventBridge/CloudWatch often gives ISO already.
    We normalize to Z format.
    """
    if not ts:
        return utc_now_iso()
    # Most AWS event times look like 2026-02-03T13:21:03Z
    if ts.endswith("Z"):
        return ts
    # fallback
    return ts


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
    """
    Put an OPEN incident. We allow duplicates by time (SK), but
    in practice detection_time is unique enough for demo.
    """
    item.setdefault("status", "OPEN")
    item.setdefault("healed_time", None)
    item.setdefault("mttr_seconds", None)

    logger.info(f"PUT incident OPEN: {json.dumps(item, default=str)}")
    table.put_item(Item=item)


def find_latest_open_incident(service: str, incident_type_prefix: str | None = None) -> dict | None:
    """
    Query newest -> oldest (ScanIndexForward=False) and return latest OPEN.
    Optionally filter by incident_type prefix like 'ALARM_' or exact type.
    """
    resp = table.query(
        KeyConditionExpression=Key("service").eq(service),
        ScanIndexForward=False,
        Limit=25,  # enough for demo, keeps it fast/cost-friendly
    )
    items = resp.get("Items", [])

    for it in items:
        if it.get("status") != "OPEN":
            continue
        if incident_type_prefix:
            t = it.get("incident_type", "")
            if incident_type_prefix.endswith("*"):
                # prefix match
                prefix = incident_type_prefix[:-1]
                if not t.startswith(prefix):
                    continue
            else:
                # exact match
                if t != incident_type_prefix:
                    continue
        return it

    return None


def resolve_incident(service: str, match_type: str | None, healed_time_iso: str, healing_action: str | None = None):
    """
    Resolve the latest matching OPEN incident:
    - match_type can be:
      - exact: "TASK_STOPPED"
      - prefix: "ALARM_*"
    """
    open_item = find_latest_open_incident(service, match_type)

    if not open_item:
        logger.warning(f"No OPEN incident found to resolve for service={service}, match_type={match_type}")
        return None

    detection_time = open_item.get("detection_time")
    mttr = seconds_between(detection_time, healed_time_iso) if detection_time else None

    update_expr = "SET #s = :resolved, healed_time = :ht, mttr_seconds = :mttr"
    expr_names = {"#s": "status"}
    expr_vals = {
        ":resolved": "RESOLVED",
        ":ht": healed_time_iso,
        ":mttr": mttr,
    }

    if healing_action:
        update_expr += ", healing_action = :ha"
        expr_vals[":ha"] = healing_action

    logger.info(f"RESOLVE incident: service={service}, detection_time={detection_time}, mttr={mttr}")

    table.update_item(
        Key={"service": service, "detection_time": detection_time},
        UpdateExpression=update_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_vals,
    )

    return {"service": service, "detection_time": detection_time, "mttr_seconds": mttr}


# -----------------------------
# Parsers: ECS + CloudWatch Alarm
# -----------------------------
def handle_ecs_task_state_change(event: dict):
    """
    EventBridge detail-type: "ECS Task State Change"
    We create incident on STOPPED, resolve on RUNNING.
    """
    detail = event.get("detail", {})
    cluster_arn = detail.get("clusterArn", "")
    group = detail.get("group", "")  # e.g. "service:healops-service"
    service = group.split("service:")[-1] if "service:" in group else "unknown-service"

    last_status = detail.get("lastStatus")
    desired_status = detail.get("desiredStatus")
    task_arn = detail.get("taskArn")
    stopped_reason = detail.get("stoppedReason")
    containers = detail.get("containers", [])
    exit_code = None
    if containers:
        exit_code = containers[0].get("exitCode")

    event_time = to_iso(event.get("time"))

    # 1) Create incident on STOPPED
    if last_status == "STOPPED" or desired_status == "STOPPED":
        item = {
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
            "healing_action": "ECS_SCHEDULER_RESTART",  # real-world: ECS service scheduler replaces task
        }
        put_open_incident(item)
        return {"action": "OPEN_CREATED", "service": service, "type": "TASK_STOPPED"}

    # 2) Resolve when task is RUNNING (simple demo correlation: resolve latest TASK_STOPPED OPEN)
    if last_status == "RUNNING" or desired_status == "RUNNING":
        resolved = resolve_incident(
            service=service,
            match_type="TASK_STOPPED",
            healed_time_iso=event_time,
            healing_action="ECS_SCHEDULER_RESTART",
        )
        return {"action": "RESOLVED", "service": service, "resolved": resolved}

    return {"action": "IGNORED", "reason": f"Unhandled ECS status last={last_status} desired={desired_status}"}


def handle_cloudwatch_alarm_state_change(event: dict):
    """
    EventBridge detail-type: "CloudWatch Alarm State Change"
    We create incident on ALARM, resolve on OK.
    """
    detail = event.get("detail", {})
    alarm_name = detail.get("alarmName", "unknown-alarm")
    state = detail.get("state", {})
    new_state = state.get("value")  # "ALARM" or "OK"
    region = event.get("region")
    event_time = to_iso(event.get("time"))

    # You can encode service in alarm name convention:
    # e.g. healops-service__cpu-high
    # We'll extract service if possible, else default.
    service = "unknown-service"
    if "__" in alarm_name:
        service = alarm_name.split("__")[0]
    elif "healops-service" in alarm_name:
        service = "healops-service"

    # Build incident_type from alarm name for uniqueness
    incident_type = f"ALARM_{alarm_name}".upper().replace(" ", "_")

    if new_state == "ALARM":
        item = {
            "service": service,
            "detection_time": event_time,
            "cluster": None,
            "component": "CloudWatch",
            "incident_type": incident_type,
            "failure_type": "ALARM",
            "failure_reason": f"CloudWatch alarm triggered: {alarm_name}",
            "detected_by": "CloudWatch",
            "alarm_name": alarm_name,
            "alarm_state": "ALARM",
            "region": region,
            "healing_action": "AUTO_REMEDIATION_PENDING",
        }
        put_open_incident(item)
        return {"action": "OPEN_CREATED", "service": service, "type": incident_type}

    if new_state == "OK":
        # Resolve latest OPEN alarm incident (prefix match)
        # We resolve by prefix "ALARM_" so any alarm is resolved correctly.
        resolved = resolve_incident(
            service=service,
            match_type="ALARM_*",
            healed_time_iso=event_time,
            healing_action="AUTO_REMEDIATION_OR_RECOVERY",
        )
        return {"action": "RESOLVED", "service": service, "resolved": resolved}

    return {"action": "IGNORED", "reason": f"Unhandled alarm state: {new_state}", "alarm": alarm_name}


# -----------------------------
# Lambda entrypoint
# -----------------------------
def handler(event, context):
    """
    Unified entrypoint for EventBridge events.
    """
    logger.info("RAW_EVENT: %s", json.dumps(event))

    detail_type = event.get("detail-type")

    if detail_type == "ECS Task State Change":
        return handle_ecs_task_state_change(event)

    if detail_type == "CloudWatch Alarm State Change":
        return handle_cloudwatch_alarm_state_change(event)

    # If you add more later (ALB target unhealthy etc.), add here without changing UI.
    return {"action": "IGNORED", "reason": f"Unsupported detail-type: {detail_type}"}
