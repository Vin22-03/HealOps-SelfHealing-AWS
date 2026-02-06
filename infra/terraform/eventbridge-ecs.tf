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
resource "aws_cloudwatch_event_rule" "healops_ecs_service_action" {
  name        = "healops-ecs-service-action"
  description = "Capture ECS Service steady state events for HealOps"

  event_pattern = jsonencode({
    source        = ["aws.ecs"]
    "detail-type" = ["ECS Service Action"]
  })
}
