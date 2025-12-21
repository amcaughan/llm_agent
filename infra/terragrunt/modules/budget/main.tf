data "aws_caller_identity" "current" {}

data "aws_ssm_parameter" "email" {
  name = var.email_param_name
}

locals {
  alert_email      = trimspace(data.aws_ssm_parameter.email.value)
  billing_view_arn = "arn:aws:billing::${data.aws_caller_identity.current.account_id}:billingview/${var.billing_view_name}"
}

resource "aws_budgets_budget" "this" {
  name        = var.budget_name
  budget_type = var.budget_type
  time_unit   = var.time_unit

  limit_amount = var.limit_amount
  limit_unit   = var.limit_unit

  billing_view_arn = local.billing_view_arn


  cost_types {
    include_credit = false
    include_refund = false
    use_amortized  = false
    use_blended    = false
  }


  dynamic "notification" {
    for_each = var.notifications
    content {
      notification_type   = notification.value.notification_type
      comparison_operator = "GREATER_THAN"
      threshold           = notification.value.threshold
      threshold_type      = "PERCENTAGE"

      subscriber_email_addresses = [local.alert_email]
      subscriber_sns_topic_arns  = [var.sns_topic_arn]
    }
  }
}
