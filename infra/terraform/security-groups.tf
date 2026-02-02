resource "aws_security_group" "alb_sg" {
  name        = "healops-alb-sg"
  description = "Security group for HealOps Application Load Balancer"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "Allow HTTP from internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "healops-alb-sg"
  }
}

resource "aws_security_group" "ecs_sg" {
  name        = "healops-ecs-sg"
  description = "Security group for HealOps ECS service"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "Allow traffic from ALB only"
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "healops-ecs-sg"
  }
}
