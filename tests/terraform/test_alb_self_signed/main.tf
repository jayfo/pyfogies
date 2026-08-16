terraform {
  required_version = "~> 1.14.0"

  backend "s3" {}

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = var.region
}

variable "region" {
  description = "AWS region in which to create resources."
  type        = string
}

variable "alb_name" {
  description = "Name of the ALB."
  type        = string
}

variable "subnet_ids" {
  description = "Subnet IDs in which to place the ALB."
  type        = set(string)
}

variable "security_group_ids" {
  description = "Security group IDs to attach to the ALB."
  type        = set(string)
}

module "alb" {
  source = "../../../terraform/alb"

  region                  = var.region
  name                    = var.alb_name
  subnet_ids              = var.subnet_ids
  security_group_ids      = var.security_group_ids
  self_signed_certificate = true
}

output "alb" {
  description = "ALB module output."
  value       = module.alb
}
