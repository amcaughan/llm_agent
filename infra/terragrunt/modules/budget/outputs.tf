output "budget_name" {
  value = aws_budgets_budget.this.name
}

output "billing_view_arn" {
  value = local.billing_view_arn
}
