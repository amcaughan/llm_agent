include "root" {
  path = find_in_parent_folders("root.hcl")
}

dependency "alerts_sns" {
  config_path = "../alerts-sns"

  mock_outputs = {
    topic_arn = "arn:aws:sns:us-east-2:000000000000:bedrock-project-alerts"
  }
  mock_outputs_allowed_terraform_commands = ["init", "plan", "validate"]
}

terraform {
  source = "${get_repo_root()}/infra/terragrunt/modules/budget"
}

inputs = {
  budget_name  = "Bedrock Project Monthly Spend"
  limit_amount = "20.0"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
  budget_type  = "COST"

  billing_view_name = "primary"

  email_param_name = "/infra/alert_email"
  sns_topic_arn    = dependency.alerts_sns.outputs.topic_arn

  notifications = [
    { notification_type = "ACTUAL", threshold = 60.0 },
    { notification_type = "ACTUAL", threshold = 100.0 },
    { notification_type = "FORECASTED", threshold = 100.0 },
  ]
}
