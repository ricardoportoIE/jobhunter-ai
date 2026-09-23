terraform {
  required_version = ">= 1.7, < 2.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
  backend "local" {}
}

provider "aws" {
  region              = "eu-west-1"
  allowed_account_ids = [var.account_id]
  default_tags {
    tags = local.tags
  }
}
