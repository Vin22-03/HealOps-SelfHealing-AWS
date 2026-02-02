terraform {
  backend "s3" {
    bucket         = "healops-terraform-state"
    key            = "infra/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "healops-terraform-locks"
    encrypt        = true
  }
}
