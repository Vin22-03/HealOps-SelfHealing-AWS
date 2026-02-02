############################################
# VPC
############################################
resource "aws_vpc" "healops_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "healops-vpc"
  }
}

############################################
# Internet Gateway
############################################
resource "aws_internet_gateway" "healops_igw" {
  vpc_id = aws_vpc.healops_vpc.id

  tags = {
    Name = "healops-igw"
  }
}

############################################
# Public Subnets (2 AZs)
############################################
resource "aws_subnet" "public_a" {
  vpc_id                  = aws_vpc.healops_vpc.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "us-east-1a"
  map_public_ip_on_launch = true

  tags = {
    Name = "healops-public-a"
  }
}

resource "aws_subnet" "public_b" {
  vpc_id                  = aws_vpc.healops_vpc.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = "us-east-1b"
  map_public_ip_on_launch = true

  tags = {
    Name = "healops-public-b"
  }
}

############################################
# Route Table
############################################
resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.healops_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.healops_igw.id
  }

  tags = {
    Name = "healops-public-rt"
  }
}

############################################
# Route Table Associations
############################################
resource "aws_route_table_association" "a" {
  subnet_id      = aws_subnet.public_a.id
  route_table_id = aws_route_table.public_rt.id
}

resource "aws_route_table_association" "b" {
  subnet_id      = aws_subnet.public_b.id
  route_table_id = aws_route_table.public_rt.id
}
