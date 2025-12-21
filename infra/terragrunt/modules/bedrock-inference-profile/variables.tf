variable "name"        { 
  type = string 
  }
variable "description" { 
  type = string
  default = null 
  }

# Foundation model id/arn
# OR an existing (system-defined) cross-region inference profile id/arn OR
# OR a provisioned throughput arn (if you’re pinning to provisioned)
variable "copy_from" { 
  type = string 
  }

variable "tags" {
  type    = map(string)
  default = {}
}
