variable "common_tags" {
  type    = map(string)
  default = {}
}

variable "profiles" {
  type = map(object({
    name        = string
    description = optional(string)
    copy_from   = string
    tags        = optional(map(string))
  }))
}
