locals {
  github_oidc_subjects = [
    "repo:${var.github_repository}:ref:refs/heads/main",
    "repo:${var.github_repository}:environment:production",
  ]
}

resource "aws_iam_openid_connect_provider" "github_actions" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [var.github_oidc_thumbprint]
}

data "aws_iam_policy_document" "github_actions_assume_role" {
  statement {
    sid     = "GitHubActionsOidc"
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github_actions.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = local.github_oidc_subjects
    }
  }
}

resource "aws_iam_role" "github_production" {
  name               = "${var.application_name}-github-production"
  assume_role_policy = data.aws_iam_policy_document.github_actions_assume_role.json
}

data "aws_iam_policy_document" "github_production" {
  statement {
    sid       = "PushApplicationImage"
    effect    = "Allow"
    actions   = ["ecr:CompleteLayerUpload", "ecr:InitiateLayerUpload", "ecr:PutImage", "ecr:UploadLayerPart"]
    resources = [aws_ecr_repository.application.arn]
  }

  statement {
    sid       = "VerifyApplicationImage"
    effect    = "Allow"
    actions   = ["ecr:DescribeImages", "ecr:DescribeRepositories"]
    resources = [aws_ecr_repository.application.arn]
  }

  statement {
    sid       = "AuthenticateToEcr"
    effect    = "Allow"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid     = "DeployThroughSsm"
    effect  = "Allow"
    actions = ["ssm:SendCommand"]
    resources = [
      var.deployment_instance_arn,
      "arn:aws:ssm:${var.aws_region}::document/AWS-RunShellScript",
    ]
  }

  statement {
    sid       = "ReadSsmCommandStatus"
    effect    = "Allow"
    actions   = ["ssm:DescribeInstanceInformation", "ssm:GetCommandInvocation"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "github_production" {
  name   = "${var.application_name}-github-production"
  role   = aws_iam_role.github_production.id
  policy = data.aws_iam_policy_document.github_production.json
}

resource "aws_iam_role" "ec2" {
  count              = var.ec2_instance_role_name == null ? 1 : 0
  name               = "${var.application_name}-ec2"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json
}

data "aws_iam_role" "existing_ec2" {
  count = var.ec2_instance_role_name == null ? 0 : 1
  name  = var.ec2_instance_role_name
}

locals {
  ec2_role_name = var.ec2_instance_role_name == null ? aws_iam_role.ec2[0].name : data.aws_iam_role.existing_ec2[0].name
}

data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy_attachment" "ec2_ssm" {
  role       = local.ec2_role_name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

data "aws_iam_policy_document" "ec2_application" {
  statement {
    sid       = "PullApplicationImage"
    effect    = "Allow"
    actions   = ["ecr:BatchCheckLayerAvailability", "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"]
    resources = [aws_ecr_repository.application.arn]
  }

  statement {
    sid       = "AuthenticateToEcr"
    effect    = "Allow"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid       = "ReadApplicationSecrets"
    effect    = "Allow"
    actions   = ["secretsmanager:DescribeSecret", "secretsmanager:GetSecretValue"]
    resources = var.secret_arns
  }
}

resource "aws_iam_role_policy" "ec2_application" {
  name   = "${var.application_name}-ec2-application"
  role   = local.ec2_role_name
  policy = data.aws_iam_policy_document.ec2_application.json
}

resource "aws_iam_instance_profile" "ec2" {
  name = "${var.application_name}-ec2"
  role = local.ec2_role_name
}
