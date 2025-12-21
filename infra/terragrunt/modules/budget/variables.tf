variable "budget_name" {
  type = string
}

variable "limit_amount" {
  type = string
}

variable "limit_unit" {
  type    = string
  default = "USD"
}

variable "time_unit" {
  type    = string
  default = "MONTHLY"
}

variable "budget_type" {
  type    = string
  default = "COST"
}

variable "billing_view_name" {
  type    = string
  default = "primary"
}

variable "email_param_name" {
  type = string
}

variable "sns_topic_arn" {
  type = string
}

variable "notifications" {
  type = list(object({
    notification_type = string # ACTUAL or FORECASTED
    threshold         = number # percent
  }))
}
