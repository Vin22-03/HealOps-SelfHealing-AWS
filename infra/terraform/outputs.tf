output "ecr_repository_url" {
  description = "ECR repository URL for HealOps application"
  value       = aws_ecr_repository.healops_app.repository_url
}
