resource "aws_ecs_task_definition" "healops" {
  family                   = "healops-task"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "512"

  execution_role_arn = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn      = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      # 🔴 CHANGE 1: Container name (THIS FIXES THE PROBE ISSUE)
      name  = "healops-app"

      # Same image repo, ECS will now pull NEW DIGEST
      image = "${aws_ecr_repository.healops.repository_url}:latest"

      essential = true

      # 🔴 CHANGE 2: Explicit command (prevents ECS reusing old metadata)
      command = [
        "uvicorn",
        "main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "3000"
      ]

      portMappings = [
        {
          containerPort = 3000
          protocol      = "tcp"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.healops.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }

      environment = [
        {
          name  = "APP_ENV"
          value = "prod"
        }
      ]
    }
  ])
}
