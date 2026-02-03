############################################
# DynamoDB: HealOps Incidents Table
############################################
resource "aws_dynamodb_table" "healops_incidents" {
  name         = "healops-incidents"
  billing_mode = "PAY_PER_REQUEST"

  hash_key  = "service"
  range_key = "detection_time"

  attribute {
    name = "service"
    type = "S"
  }

  attribute {
    name = "detection_time"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  global_secondary_index {
    name            = "status-index"
    hash_key        = "status"
    range_key       = "detection_time"
    projection_type = "ALL"
  }

  tags = {
    Name = "healops-incidents"
  }
}
