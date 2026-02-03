############################################
# EventBridge: ECS Task STOPPED (HealOps)
############################################
resource "aws_cloudwatch_event_rule" "ecs_task_stopped" {
  name        = "healops-ecs-task-stopped"
  description = "Capture all ECS task STOPPED events in healops-cluster"

  event_pattern = jsonencode({
    source        = ["aws.ecs"],
    "detail-type" = ["ECS Task State Change"],
    detail = {
      clusterArn = [aws_ecs_cluster.healops_cluster.arn],
      lastStatus = ["STOPPED"]
    }
  })
}
