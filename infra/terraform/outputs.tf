output "healops_incidents_table_name" {
  value = aws_dynamodb_table.healops_incidents.name
}

output "healops_incidents_table_arn" {
  value = aws_dynamodb_table.healops_incidents.arn
}

output "ecr_repository_url" {
  description = "ECR repository URL for HealOps application"
  value       = aws_ecr_repository.healops_app.repository_url
}
