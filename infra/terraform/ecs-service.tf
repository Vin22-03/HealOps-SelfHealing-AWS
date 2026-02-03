resource "aws_ecs_service" "healops_service" {
  name            = "healops-service"
  cluster         = aws_ecs_cluster.healops_cluster.id
  task_definition = aws_ecs_task_definition.healops_task.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = [aws_subnet.public_a.id, aws_subnet.public_b.id]
    security_groups  = [aws_security_group.ecs_sg.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.healops_tg.arn
    container_name   = "healops-probe"
    container_port   = 3000
  }

  depends_on = [
    aws_lb_listener.healops_listener
  ]
}
