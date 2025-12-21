variable "topic_name" {
  type = string
}

variable "email_param_name" {
  type = string
}

# Publisher allowlist. Each entry becomes one SNS topic-policy statement.
# principal_type examples: "Service", "AWS"
# examples:
#   - Service: ["cloudwatch.amazonaws.com"]
#   - AWS: ["arn:aws:iam::123456789012:role/MyRole", "arn:aws:iam::123456789012:root"]
variable "publisher_statements" {
  type = list(object({
    sid                   = string
    principal_type        = string
    principal_identifiers = list(string)

    actions = optional(list(string), ["sns:Publish"])

    # Optional conditions in aws_iam_policy_document condition-block format
    conditions = optional(list(object({
      test     = string
      variable = string
      values   = list(string)
    })), [])
  }))
  default = []
}
