locals {
  bedrock_resources = length(var.model_arns) > 0 ? var.model_arns : ["*"]
}

data "aws_iam_policy_document" "bedrock_invoke" {
  statement {
    sid    = "BedrockInvoke"
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream"
    ]
    resources = local.bedrock_resources
  }
}

resource "aws_iam_policy" "this" {
  name   = "${var.name}-bedrock-invoke"
  policy = data.aws_iam_policy_document.bedrock_invoke.json
}

data "aws_iam_policy_document" "assume_role" {
  statement {
    sid    = "AssumeRoleService"
    effect = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = [var.service_principal]
    }
  }

  dynamic "statement" {
    for_each = length(var.additional_trust_principals) > 0 ? [1] : []
    content {
      sid    = "AssumeRoleAdditionalAWSPrincipals"
      effect = "Allow"
      actions = ["sts:AssumeRole"]

      principals {
        type        = "AWS"
        identifiers = var.additional_trust_principals
      }
    }
  }
}

resource "aws_iam_role" "this" {
  count              = var.create_role ? 1 : 0
  name               = "${var.name}-bedrock"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
}

resource "aws_iam_role_policy_attachment" "attach" {
  count      = var.create_role ? 1 : 0
  role       = aws_iam_role.this[0].name
  policy_arn = aws_iam_policy.this.arn
}
