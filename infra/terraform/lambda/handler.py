import json
import boto3
import os
from datetime import datetime, timezone

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ.get("INCIDENTS_TABLE", "healops-incidents")
table = dynamodb.Table(TABLE_NAME)


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def lambda_handler(event, context):
    print("RAW_EVENT:", json.dumps(event))

    detail = event.get("detail", {})
    last_status = detail.get("lastStatus")
    desired_status = detail.get("desiredStatus")
    cluster_arn = detail.get("clusterArn", "")
    group = detail.get("group", "")
    containers = detail.get("containers", [])

    service_name = group.replace("service:", "") if group else "unknown"
    cluster_name = cluster_arn.split("/")[-1] if cluster_arn else "unknown"

    exit_code = None
    if containers:
        exit_code = containers[0].get("exitCode")

    detection_time = now_utc()

    # -------------------------------
    # CASE 1: TASK STOPPED → OPEN INCIDENT
    # -------------------------------
    if last_status == "STOPPED":
        print("Detected TASK_STOPPED for service:", service_name)

        item = {
            "service": service_name,
            "detection_time": detection_time,
            "cluster": cluster_name,
            "component": "ECS",
            "desired_status": "STOPPED",
            "detected_by": "EventBridge",
            "exit_code": exit_code,
            "failure_type": "TASK_STOPPED",
            "status": "OPEN",
            "healed_time": None,
            "mttr_seconds": None
        }

        table.put_item(Item=item)
        print("Incident OPENED:", item)

        return {"status": "OPEN_RECORDED"}

    # -------------------------------
    # CASE 2: SERVICE HEALED → RESOLVE INCIDENT
    # ECS does NOT always emit RUNNING,
    # so we resolve based on desiredStatus
    # -------------------------------
    if desired_status == "RUNNING":
        print("Detected desiredStatus RUNNING → resolving incident")

        # Find latest OPEN incident
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key("service").eq(service_name),
            ScanIndexForward=False
        )

        for item in response.get("Items", []):
            if item.get("status") == "OPEN":
                healed_time = now_utc()

                start = datetime.fromisoformat(item["detection_time"])
                end = datetime.fromisoformat(healed_time)
                mttr = int((end - start).total_seconds())

                table.update_item(
                    Key={
                        "service": item["service"],
                        "detection_time": item["detection_time"]
                    },
                    UpdateExpression="""
                        SET
                            #s = :resolved,
                            healed_time = :healed,
                            mttr_seconds = :mttr
                    """,
                    ExpressionAttributeNames={
                        "#s": "status"
                    },
                    ExpressionAttributeValues={
                        ":resolved": "RESOLVED",
                        ":healed": healed_time,
                        ":mttr": mttr
                    }
                )

                print("Incident RESOLVED for service:", service_name)
                return {"status": "RESOLVED"}

    print("No action taken")
    return {"status": "IGNORED"}
