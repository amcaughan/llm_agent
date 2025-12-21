resource "aws_sns_topic" "this" {
  name = var.topic_name
  # I would use a key in a professional account, but I don't want to pay for one here lol
  # kms_master_key_id = "alias/aws/sns"
}

data "aws_ssm_parameter" "email" {
  name = var.email_param_name
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.this.arn
  protocol  = "email"
  endpoint  = trimspace(data.aws_ssm_parameter.email.value)
}

# Attach a topic policy only if you have publisher statements.
data "aws_iam_policy_document" "topic_policy" {
  count = length(var.publisher_statements) > 0 ? 1 : 0

  dynamic "statement" {
    for_each = var.publisher_statements
    content {
      sid    = statement.value.sid
      effect = "Allow"

      principals {
        type        = statement.value.principal_type
        identifiers = statement.value.principal_identifiers
      }

      actions   = statement.value.actions
      resources = [aws_sns_topic.this.arn]

      dynamic "condition" {
        for_each = statement.value.conditions
        content {
          test     = condition.value.test
          variable = condition.value.variable
          values   = condition.value.values
        }
      }
    }
  }
}

resource "aws_sns_topic_policy" "this" {
  count  = length(var.publisher_statements) > 0 ? 1 : 0
  arn    = aws_sns_topic.this.arn
  policy = data.aws_iam_policy_document.topic_policy[0].json
}
