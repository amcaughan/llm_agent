output "profile_arns" {
  value = { for k, m in module.profile : k => m.arn }
}

output "profile_ids" {
  value = { for k, m in module.profile : k => m.id }
}
