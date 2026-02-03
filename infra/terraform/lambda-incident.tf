############################################
# Lambda: HealOps Incident Ingestor
############################################
resource "aws_lambda_function" "healops_incident_lambda" {
  function_name = "healops-incident-ingestor"
  role          = aws_iam_role.healops_lambda_role.arn
  runtime       = "python3.11"
  handler       = "handler.lambda_handler"

  filename         = "lambda/incident_lambda.zip"
  source_code_hash = filebase64sha256("lambda/incident_lambda.zip")

  timeout = 10

  environment {
    variables = {
      INCIDENTS_TABLE = aws_dynamodb_table.healops_incidents.name
      AWS_REGION      = var.aws_region
    }
  }
}
