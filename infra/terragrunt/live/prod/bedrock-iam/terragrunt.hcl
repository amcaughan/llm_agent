include "root" {
  path = find_in_parent_folders("root.hcl")
}

terraform {
  source = "${get_repo_root()}/infra/terragrunt/modules/bedrock-iam"
}

inputs = {
  name = "bedrock-project"

  model_arns = [
    "arn:aws:bedrock:*::foundation-model/*",
    "arn:aws:bedrock:*::inference-profile/*"
  ]

  create_role       = true
  service_principal = "lambda.amazonaws.com"
  additional_trust_principals = []
}
