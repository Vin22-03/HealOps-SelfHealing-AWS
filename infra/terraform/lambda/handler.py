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
                prefix = incident_type_prefix[:-1]
                if not t.startswith(prefix):
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

    # extra fields (desired/running after, scale_delta, etc.)
    if extra_updates:
        for k, v in extra_updates.items():
            placeholder = f":{k}"
            update_expr += f", {k} = {placeholder}"
            expr_vals[placeholder] = v

    logger.info("RESOLVE incident: service=%s detection_time=%s mttr=%s", service, detection_time, mttr)

    table.update_item(
        Key={"service": service, "detection_time": detection_time},
        UpdateExpression=update_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_vals,
    )

    return {"service": service, "detection_time": detection_time, "mttr_seconds": mttr}


def get_ecs_service_counts(cluster: str, service: str) -> dict | None:
    """
    Reads real ECS service state to prove scaling.
    """
    try:
        resp = ecs.describe_services(cluster=cluster, services=[service])
        svcs = resp.get("services", [])
        if not svcs:
            logger.warning("DescribeServices returned no services for cluster=%s service=%s", cluster, service)
            return None

        s = svcs[0]
        return {
            "desired": s.get("desiredCount"),
            "running": s.get("runningCount"),
            "pending": s.get("pendingCount"),
        }
    except Exception as e:
        logger.exception("Failed DescribeServices cluster=%s service=%s err=%s", cluster, service, str(e))
        return None


def parse_targettracking_alarm_name(alarm_name: str) -> tuple[str | None, str | None]:
    """
    Expected format:
      TargetTracking-service/<cluster>/<service>-AlarmHigh-<id>
      TargetTracking-service/<cluster>/<service>-AlarmLow-<id>

    Returns (cluster, service) if parsable.
    """
    try:
        prefix = "TargetTracking-service/"
        if not alarm_name.startswith(prefix):
            return (None, None)

        rest = alarm_name[len(prefix):]  # <cluster>/<service>-AlarmHigh-...
        parts = rest.split("/", 1)
        if len(parts) != 2:
            return (None, None)

        cluster = parts[0]
        service_plus = parts[1]  # e.g., healops-service-AlarmHigh-xxxx
        # strip everything from "-Alarm" onwards to get service name
        idx = service_plus.find("-Alarm")
        service = service_plus[:idx] if idx != -1 else service_plus

        return (cluster, service)
    except Exception:
        return (None, None)


# -----------------------------
# Parsers: ECS + CloudWatch Alarm
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

    exit_code = None
    if containers:
        exit_code = containers[0].get("exitCode")

    event_time = to_iso(event.get("time"))

    # OPEN on STOPPED
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
            "healing_action": "ECS_SCHEDULER_RESTART",
        }
        put_open_incident(item)
        return {"action": "OPEN_CREATED", "service": service, "type": "TASK_STOPPED"}

    # RESOLVE on RUNNING
    if last_status == "RUNNING" or desired_status == "RUNNING":
        resolved = resolve_incident(
            service=service,
            match_type="TASK_STOPPED",
            healed_time_iso=event_time,
            healing_action="ECS_SCHEDULER_RESTART",
        )
        return {"action": "RESOLVED", "service": service, "resolved": resolved}

    return {"action": "IGNORED", "reason": f"Unhandled ECS status last={last_status} desired={desired_status}"}


def _extract_service_from_alarm_event(detail: dict) -> str:
    alarm_name = detail.get("alarmName", "")

    # ✅ TargetTracking alarm name parsing (preferred)
    cluster, service = parse_targettracking_alarm_name(alarm_name)
    if service:
        return service

    # 1) naming convention: service__cpu-high (legacy)
    if "__" in alarm_name:
        return alarm_name.split("__")[0]

    # 2) metric dimensions in alarm config
    cfg = detail.get("configuration", {})
    metrics = cfg.get("metrics", []) or []
    for m in metrics:
        metric_stat = m.get("metricStat", {}).get("metric", {})
        dims = metric_stat.get("dimensions", {}) or {}
        if "ServiceName" in dims:
            return dims["ServiceName"]

    if "healops-service" in alarm_name:
        return "healops-service"

    return DEFAULT_SERVICE_NAME


def _extract_cluster_from_alarm_event(detail: dict) -> str | None:
    alarm_name = detail.get("alarmName", "")
    cluster, _ = parse_targettracking_alarm_name(alarm_name)
    return cluster


def handle_cloudwatch_alarm_state_change(event: dict):
    detail = event.get("detail", {})
    alarm_name = detail.get("alarmName", "unknown-alarm")
    state = detail.get("state", {})
    new_state = state.get("value")  # ALARM / OK
    region = event.get("region")
    event_time = to_iso(event.get("time"))

    service = _extract_service_from_alarm_event(detail)
    cluster = _extract_cluster_from_alarm_event(detail)
    incident_type = f"ALARM_{alarm_name}".upper().replace(" ", "_")

    # Capture counts if we can
    counts = None
    if cluster and service:
        counts = get_ecs_service_counts(cluster=cluster, service=service)

    if new_state == "ALARM":
        item = {
            "service": service,
            "detection_time": event_time,
            "cluster": cluster,
            "component": "CloudWatch",
            "incident_type": incident_type,
            "failure_type": "ALARM",
            "failure_reason": f"CloudWatch alarm triggered: {alarm_name}",
            "detected_by": "CloudWatch",
            "alarm_name": alarm_name,
            "alarm_state": "ALARM",
            "region": region,
            "healing_action": "ECS_TARGET_TRACKING_AUTOSCALING_PENDING",
        }

        if counts:
            item["desired_before"] = counts.get("desired")
            item["running_before"] = counts.get("running")
            item["pending_before"] = counts.get("pending")

        put_open_incident(item)
        return {"action": "OPEN_CREATED", "service": service, "type": incident_type, "counts_before": counts}

    if new_state == "OK":
        extra = {}
        if counts:
            extra["desired_after"] = counts.get("desired")
            extra["running_after"] = counts.get("running")
            extra["pending_after"] = counts.get("pending")

            # compute scale delta if we can read OPEN item
            open_item = find_latest_open_incident(service, "ALARM_*")
            if open_item:
                db = open_item.get("desired_before")
                da = counts.get("desired")
                if isinstance(db, int) and isinstance(da, int):
                    extra["scale_delta"] = da - db

        resolved = resolve_incident(
            service=service,
            match_type="ALARM_*",
            healed_time_iso=event_time,
            healing_action="ECS_TARGET_TRACKING_AUTOSCALING",
            extra_updates=extra if extra else None,
        )
        return {"action": "RESOLVED", "service": service, "resolved": resolved, "counts_after": counts}

    return {"action": "IGNORED", "reason": f"Unhandled alarm state: {new_state}", "alarm": alarm_name}


# -----------------------------
# Lambda entrypoint
# -----------------------------
def lambda_handler(event, context):
    try:
        logger.info("RAW_EVENT: %s", json.dumps(event))
        detail_type = event.get("detail-type")

        if detail_type == "ECS Task State Change":
            return handle_ecs_task_state_change(event)

        if detail_type == "CloudWatch Alarm State Change":
            return handle_cloudwatch_alarm_state_change(event)

        return {"action": "IGNORED", "reason": f"Unsupported detail-type: {detail_type}"}

    except Exception as e:
        logger.exception("FAILED processing event: %s", str(e))
        raise


def handler(event, context):
    return lambda_handler(event, context)
