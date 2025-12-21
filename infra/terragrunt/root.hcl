locals {
  aws_region  = "us-east-2"
  aws_profile = "default"

  # Project-specific tags
  common_tags = {
    Project   = "bedrock_project"
    Owner     = "amcaughan"
    ManagedBy = "terragrunt"
  }

  # Set up in my aws_infra core management repo
  state_bucket = "amcaughan-tf-state-us-east-2"
}

remote_state {
  backend = "s3"

  config = {
    bucket       = local.state_bucket
    key          = "${path_relative_to_include()}/terraform.tfstate"
    region       = local.aws_region
    encrypt      = true
    use_lockfile = true
  }
}

generate "provider" {
  path      = "provider.tf"
  if_exists = "overwrite_terragrunt"

  contents = <<EOF
provider "aws" {
  region  = "${local.aws_region}"
  profile = "${local.aws_profile}"

  default_tags {
    tags = ${jsonencode(local.common_tags)}
  }
}
EOF
}

generate "backend_stub" {
  path      = "backend.tf"
  if_exists = "overwrite_terragrunt"

  contents = <<EOF
terraform {
  backend "s3" {}
}
EOF
}
