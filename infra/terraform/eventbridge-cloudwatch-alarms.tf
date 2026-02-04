############################################
# EventBridge: CloudWatch Alarm State Change
############################################
resource "aws_cloudwatch_event_rule" "healops_cw_alarm_state_change" {
  name        = "healops-cw-alarm-state-change"
  description = "Capture CloudWatch alarm ALARM/OK events for HealOps"

  event_pattern = jsonencode({
    source        = ["aws.cloudwatch"],
    "detail-type" = ["CloudWatch Alarm State Change"]
  })
}

############################################
# Target: Send alarm events to HealOps Lambda
############################################
resource "aws_cloudwatch_event_target" "healops_cw_alarm_target" {
  rule      = aws_cloudwatch_event_rule.healops_cw_alarm_state_change.name
  target_id = "healops-incident-lambda-cw"
  arn       = aws_lambda_function.healops_incident_lambda.arn
}

############################################
# Permission: Allow this EventBridge rule to invoke Lambda
############################################
resource "aws_lambda_permission" "allow_eventbridge_invoke_cw_alarm" {
  statement_id  = "AllowExecutionFromEventBridgeCWAlarm"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.healops_incident_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.healops_cw_alarm_state_change.arn
}
