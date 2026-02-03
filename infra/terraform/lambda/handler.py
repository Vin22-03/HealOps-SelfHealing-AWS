import json
import boto3
import os
from datetime import datetime, timezone

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["INCIDENTS_TABLE"])


def lambda_handler(event, context):
    print("RAW_EVENT:", json.dumps(event))

    detail = event.get("detail", {})
    last_status = detail.get("lastStatus")
    cluster_arn = detail.get("clusterArn", "")
    service_arn = detail.get("group", "")

    if not service_arn.startswith("service:"):
        return {"message": "Not a service task, ignoring"}

    service_name = service_arn.replace("service:", "")
    cluster_name = cluster_arn.split("/")[-1]
    now = datetime.now(timezone.utc).isoformat()

    # -------------------------------
    # FAILURE: TASK STOPPED
    # -------------------------------
    if last_status == "STOPPED":
        item = {
            "service": service_name,
            "detection_time": now,
            "cluster": cluster_name,
            "component": "ECS",
            "desired_status": "STOPPED",
            "detected_by": "EventBridge",
            "failure_type": "TASK_STOPPED",
            "exit_code": detail.get("containers", [{}])[0].get("exitCode"),
            "status": "OPEN",
            "healed_time": None,
            "mttr_seconds": None,
            "healing_action": "ECS Scheduler"
        }

        table.put_item(Item=item)
        print("Incident CREATED:", item)

        return {"message": "STOPPED incident recorded"}

    # -------------------------------
    # RECOVERY: TASK RUNNING
    # -------------------------------
    if last_status == "RUNNING":
        response = table.query(
            KeyConditionExpression="service = :svc",
            ExpressionAttributeValues={
                ":svc": service_name
            },
            ScanIndexForward=False,  # latest first
            Limit=1
        )

        if not response["Items"]:
            print("No incident found to resolve")
            return {"message": "No incident to resolve"}

        incident = response["Items"][0]

        if incident.get("status") != "OPEN":
            print("Latest incident already resolved")
            return {"message": "Incident already resolved"}

        detection_time = datetime.fromisoformat(incident["detection_time"])
        healed_time = datetime.now(timezone.utc)
        mttr = int((healed_time - detection_time).total_seconds())

        table.update_item(
            Key={
                "service": incident["service"],
                "detection_time": incident["detection_time"]
            },
            UpdateExpression="""
                SET
                    healed_time = :healed,
                    mttr_seconds = :mttr,
                    #s = :status
            """,
            ExpressionAttributeNames={
                "#s": "status"
            },
            ExpressionAttributeValues={
                ":healed": healed_time.isoformat(),
                ":mttr": mttr,
                ":status": "RESOLVED"
            }
        )

        print("Incident RESOLVED:", incident["service"], mttr, "seconds")

        return {"message": "Incident resolved"}

    return {"message": "Event ignored"}
