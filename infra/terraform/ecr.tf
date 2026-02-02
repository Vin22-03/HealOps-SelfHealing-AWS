resource "aws_ecr_repository" "healops_app" {
  name                 = "healops-app"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "healops-app"
  }
}
