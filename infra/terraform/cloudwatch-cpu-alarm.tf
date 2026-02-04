############################################
# CloudWatch Alarm: ECS Service CPU High
############################################
resource "aws_cloudwatch_metric_alarm" "healops_cpu_high" {
  alarm_name          = "healops-service__cpu-high"
  alarm_description   = "High CPU detected for healops-service (HealOps incident source)"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  threshold           = 60

  metric_name = "CPUUtilization"
  namespace   = "AWS/ECS"
  statistic   = "Average"
  period      = 60

  dimensions = {
    ClusterName = aws_ecs_cluster.healops_cluster.name
    ServiceName = aws_ecs_service.healops_service.name
  }

  treat_missing_data = "notBreaching"
}
