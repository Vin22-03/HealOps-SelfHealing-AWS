############################################
# Allow EventBridge to invoke Lambda
############################################
resource "aws_lambda_permission" "allow_eventbridge_invoke" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.healops_incident_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ecs_task_stopped.arn
}

############################################
# Attach Lambda as target to ECS STOPPED rule
############################################
resource "aws_cloudwatch_event_target" "ecs_task_stopped_target" {
  rule      = aws_cloudwatch_event_rule.ecs_task_stopped.name
  target_id = "healops-incident-lambda"
  arn       = aws_lambda_function.healops_incident_lambda.arn
}
