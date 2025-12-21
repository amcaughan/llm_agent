resource "aws_bedrock_inference_profile" "this" {
  name        = var.name
  description = var.description

  model_source {
    # Per provider docs, copy_from can be a foundation model identifier, an inference profile id/arn,
    # or a provisioned throughput arn (depending on Bedrock support).
    copy_from = var.copy_from
  }

  tags = var.tags
}
