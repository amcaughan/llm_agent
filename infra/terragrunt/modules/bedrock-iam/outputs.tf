output "policy_arn" {
  value = aws_iam_policy.this.arn
}

output "role_arn" {
  value       = try(aws_iam_role.this[0].arn, null)
  description = "Null if create_role=false"
}

output "role_name" {
  value       = try(aws_iam_role.this[0].name, null)
  description = "Null if create_role=false"
}
