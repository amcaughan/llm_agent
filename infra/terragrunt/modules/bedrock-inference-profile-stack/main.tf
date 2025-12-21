module "profile" {
  source   = "../bedrock-inference-profile"
  for_each = var.profiles

  name        = each.value.name
  description = try(each.value.description, null)
  copy_from   = each.value.copy_from

  # Merge common tags + per-profile tags
  tags = merge(var.common_tags, try(each.value.tags, {}))
}
