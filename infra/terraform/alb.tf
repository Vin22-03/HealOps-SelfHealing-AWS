############################################
# Application Load Balancer
############################################
resource "aws_lb" "healops_alb" {
  name               = "healops-alb"
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg.id]

  subnets = [
    aws_subnet.public_a.id,
    aws_subnet.public_b.id
  ]

  tags = {
    Name = "healops-alb"
  }
}

############################################
# Target Group (FIXED + SAFE REPLACEMENT)
############################################
resource "aws_lb_target_group" "healops_tg" {
  name_prefix = "healtg"
  port        = 3000 # ✅ MUST match container port
  protocol    = "HTTP"
  vpc_id      = aws_vpc.healops_vpc.id
  target_type = "ip"

  health_check {
    path                = "/health"
    protocol            = "HTTP"
    port                = "traffic-port"
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    matcher             = "200"
  }

  # 🔥 CRITICAL FIX (prevents ResourceInUse error)
  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "healops-tg"
  }
}

############################################
# ALB Listener (NO CHANGE NEEDED)
############################################
resource "aws_lb_listener" "healops_listener" {
  load_balancer_arn = aws_lb.healops_alb.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.healops_tg.arn
  }
}
