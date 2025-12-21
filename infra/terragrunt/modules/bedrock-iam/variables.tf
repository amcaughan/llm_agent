variable "name" {
  type = string
}

# If empty => allow invoke on "*"
variable "model_arns" {
  type    = list(string)
  default = []
}

# If true, create an IAM role and attach the policy.
variable "create_role" {
  type    = bool
  default = true
}

# [ lambda.amazonaws.com, ecs-tasks.amazonaws.com, ec2.amazonaws.com]
# Or provide AWS principal ARNs via additional_trust_principals.
variable "service_principal" {
  type    = string
  default = "lambda.amazonaws.com"
}

# Additional AWS principals allowed to assume the role (e.g., a CI role, or another account role ARN)
variable "additional_trust_principals" {
  type    = list(string)
  default = []
}
