############################################
# ECS Service Auto Scaling Target
############################################
resource "aws_appautoscaling_target" "healops_ecs_desired_count" {
  service_namespace  = "ecs"
  scalable_dimension = "ecs:service:DesiredCount"

  resource_id = "service/${aws_ecs_cluster.healops_cluster.name}/${aws_ecs_service.healops_service.name}"

  min_capacity = 1
  max_capacity = 3
}

############################################
# Target Tracking Scaling Policy (CPU)
############################################
resource "aws_appautoscaling_policy" "healops_cpu_target_tracking" {
  name        = "healops-cpu-target-tracking"
  policy_type = "TargetTrackingScaling"

  resource_id        = aws_appautoscaling_target.healops_ecs_desired_count.resource_id
  scalable_dimension = aws_appautoscaling_target.healops_ecs_desired_count.scalable_dimension
  service_namespace  = aws_appautoscaling_target.healops_ecs_desired_count.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }

    target_value       = 50
    scale_in_cooldown  = 60
    scale_out_cooldown = 30
  }
}
