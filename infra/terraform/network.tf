# Use default VPC
data "aws_vpc" "default" {
  default = true
}

# Fetch public subnets from default VPC
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}
