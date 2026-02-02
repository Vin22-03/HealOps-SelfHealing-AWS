resource "aws_ecs_cluster" "healops_cluster" {
  name = "healops-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = "healops-cluster"
  }
}
