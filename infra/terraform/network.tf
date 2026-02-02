############################################
# Use default VPC
############################################
data "aws_vpc" "default" {
  default = true
}

############################################
# Fetch ONLY public subnets from default VPC
# (Required for ALB – multi-AZ + internet-facing)
############################################
data "aws_subnets" "public" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }

  filter {
    name   = "map-public-ip-on-launch"
    values = ["true"]
  }
}
