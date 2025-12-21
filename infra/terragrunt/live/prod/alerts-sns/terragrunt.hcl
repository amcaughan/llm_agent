include "root" {
  path = find_in_parent_folders("root.hcl")
}

terraform {
  source = "${get_repo_root()}/infra/terragrunt/modules/alerts-sns"
}

inputs = {
  topic_name       = "bedrock-project-alerts"
  email_param_name = "/infra/alert_email"

  publisher_statements = []
}
