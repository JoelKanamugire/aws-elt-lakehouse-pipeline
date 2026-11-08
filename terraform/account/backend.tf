terraform {
  backend "s3" {
    bucket         = "datadevp-tfstate"
    key            = "account/terraform.tfstate"
    region         = "us-east-2"
    dynamodb_table = "datadevp-tfstate-lock"
    encrypt        = true
  }
}