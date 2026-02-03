import os
import json
import uuid
from datetime import datetime, timezone

import boto3

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["INCIDENTS_TABLE"]
table = dynamodb.Table(TABLE_NAME)


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def lambda_handler(event, context):
    # Log the raw event (super useful for debugging first runs)
    print("RAW_EVENT:", json.dumps(event))

    detail = event.get("detail", {})
    last_status = detail.get("lastStatus")

    # We only care about STOPPED (rule should already filter, this is a safety net)
    if last_status != "STOPPED":
        return {"ignored": True, "reason": f"lastStatus={last_status}"}

    cluster_arn = detail.get("clusterArn", "")
    group = detail.get("group", "")  # often like: service:healops-service
    task_arn = detail.get("taskArn", "")
    stopped_reason = detail.get("stoppedReason", "")
    desired_status = detail.get("desiredStatus", "")

    # Best-effort exit code (may not exist sometimes)
    exit_code = None
    containers = detail.get("containers", [])
    if containers and isinstance(containers, list):
        exit_code = containers[0].get("exitCode")

    detection_time = event.get("time") or iso_now()

    # Service name extraction (best effort)
    service_name = "unknown"
    if group.startswith("service:"):
        service_name = group.split("service:", 1)[1]

    incident_id = f"INC-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(uuid.uuid4())[:8]}"

    item = {
        "service": service_name,
        "detection_time": detection_time,

        "incident_id": incident_id,
        "cluster": cluster_arn.split("/")[-1] if "/" in cluster_arn else cluster_arn,
        "region": os.environ.get("AWS_REGION", "us-east-1"),

        "component": "ECS",
        "failure_type": "TASK_STOPPED",
        "severity": "P2",

        "task_arn": task_arn,
        "desired_status": desired_status,
        "exit_code": exit_code,
        "stop_reason": stopped_reason,

        "detected_by": "EventBridge",
        "raw_event_id": event.get("id", ""),

        # Healing fields will be filled in next iteration once we track recovery
        "healing_action": "ECS_SCHEDULER_RESTART",
        "healed_time": None,
        "mttr_seconds": None,

        "status": "OPEN",
        "learning": "Captured STOPPED event; recovery tracking pending."
    }

    table.put_item(Item=item)

    return {"stored": True, "incident_id": incident_id, "service": service_name}
