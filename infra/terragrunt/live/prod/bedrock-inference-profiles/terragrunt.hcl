include "root" {
  path = find_in_parent_folders("root.hcl")
}

terraform {
  source = "${get_repo_root()}/infra/terragrunt//modules/bedrock-inference-profile-stack"
}

inputs = {

  profiles = {
    large = {
      name        = "bedrock-project-large"
      description = "High-Power model"
      copy_from   = "anthropic.claude-opus-4-5-20251101-v1:0"
    }

    small = {
      name      = "bedrock-project-small"
      description = "Low-Power model"
      copy_from = "anthropic.claude-haiku-4-5-20251001-v1:0"
    }
  }
}
