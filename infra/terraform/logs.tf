resource "aws_cloudwatch_log_group" "healops_logs" {
  name              = "/ecs/healops"
  retention_in_days = 7

  tags = {
    Name = "healops-ecs-logs"
  }
}
