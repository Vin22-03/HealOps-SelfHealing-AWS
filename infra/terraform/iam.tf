############################
# ECS Execution Role
############################

resource "aws_iam_role" "ecs_execution_role" {
  name = "healops-ecs-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

############################
# ECS Task Role (App Role)
############################

resource "aws_iam_role" "ecs_task_role" {
  name = "healops-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

############################################
# 🔥 ADD: ECS Task Role → DynamoDB READ
############################################

resource "aws_iam_policy" "ecs_task_dynamodb_read" {
  name = "healops-ecs-task-dynamodb-read"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "dynamodb:Scan",
          "dynamodb:Query",
          "dynamodb:GetItem"
        ],
        Resource = aws_dynamodb_table.healops_incidents.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_dynamodb_attach" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.ecs_task_dynamodb_read.arn
}

############################################
# IAM Role for HealOps Incident Lambda
############################################

resource "aws_iam_role" "healops_lambda_role" {
  name = "healops-incident-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      },
      Action = "sts:AssumeRole"
    }]
  })
}

############################################
# IAM Policy: Lambda logging + DynamoDB write + ECS read
############################################

resource "aws_iam_policy" "healops_lambda_policy" {
  name = "healops-incident-lambda-policy"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow",
        Action = [
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:GetItem",
          "dynamodb:Query"
        ],
        Resource = aws_dynamodb_table.healops_incidents.arn
      },
      {
        # 🔹 REQUIRED for autoscaling evidence capture
        Effect = "Allow",
        Action = [
          "ecs:DescribeServices"
        ],
        Resource = "*"
      }
    ]
  })
}

############################################
# Attach policy to Lambda role
############################################

resource "aws_iam_role_policy_attachment" "healops_lambda_attach" {
  role       = aws_iam_role.healops_lambda_role.name
  policy_arn = aws_iam_policy.healops_lambda_policy.arn
}
