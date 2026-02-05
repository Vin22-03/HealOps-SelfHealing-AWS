resource "aws_ecs_task_definition" "healops" {
  family                   = "healops-task"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "512"

  execution_role_arn = aws_iam_role.ecs_execution_role.arn
  task_role_arn      = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      # ✅ Correct container identity (NO probe confusion)
      name = "healops-app"

      # ✅ Correct app image
      image = "${aws_ecr_repository.healops_app.repository_url}:latest"

      essential = true

      # ✅ Explicit app start command
      command = [
        "uvicorn",
        "main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "3000"
      ]

      # ✅ Port mapping (matches ALB + Dockerfile)
      portMappings = [
        {
          containerPort = 3000
          protocol      = "tcp"
        }
      ]


      # ✅ Logs
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.healops_logs.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])
}
