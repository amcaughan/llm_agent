include "root" {
  path = find_in_parent_folders("root.hcl")
}

dependency "inference_profiles" {
  config_path  = "../bedrock-inference-profiles"
  skip_outputs = true
}

terraform {
  source = "${get_repo_root()}/infra/terragrunt/modules/bedrock-iam"
}

inputs = {
  name = "bedrock-project"

  # Add any models defined in the inference profiles /live folder, plus foundation models
  model_arns = distinct(concat(
    ["arn:aws:bedrock:*::foundation-model/*"],
    values(try(dependency.inference_profiles.outputs.profile_arns, {}))
  ))

  create_role       = true
  service_principal = "lambda.amazonaws.com"
  additional_trust_principals = []
}
