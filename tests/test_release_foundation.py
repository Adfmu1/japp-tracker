from pathlib import Path

ROOT = Path(__file__).parents[1]
TERRAFORM = ROOT / "infra/aws"


def read_infra(name: str) -> str:
    return (TERRAFORM / name).read_text()


def test_aws_bootstrap_declares_private_ecr_and_bounded_lifecycle_policy():
    repository = read_infra("ecr.tf")

    assert 'resource "aws_ecr_repository" "application"' in repository
    assert 'image_tag_mutability = "IMMUTABLE"' in repository
    assert 'resource "aws_ecr_lifecycle_policy" "application"' in repository
    assert 'tagStatus     = "tagged"' in repository
    assert 'tagPrefixList = ["sha-"]' in repository
    assert "countNumber   = 20" in repository


def test_aws_bootstrap_restricts_github_oidc_to_main_and_production():
    iam = read_infra("iam.tf")

    assert "token.actions.githubusercontent.com:sub" in iam
    assert "repo:${var.github_repository}:ref:refs/heads/main" in iam
    assert "repo:${var.github_repository}:environment:production" in iam
    assert "repo:${var.github_repository}:*" not in iam
    assert 'resource "aws_iam_openid_connect_provider" "github_actions"' in iam


def test_github_ssm_send_command_is_limited_to_the_approved_instance_and_document():
    iam = read_infra("iam.tf")

    send_command = iam[iam.index('sid     = "DeployThroughSsm"') :]
    send_command = send_command[: send_command.index("  }\n\n  statement")]
    assert '"ssm:SendCommand"' in send_command
    assert "var.deployment_instance_arn" in send_command
    assert "AWS-RunShellScript" in send_command
    assert 'resources = ["*"]' not in send_command


def test_ec2_role_is_limited_to_ecr_pull_ssm_and_named_secret_reads():
    iam = read_infra("iam.tf")

    assert "AmazonSSMManagedInstanceCore" in iam
    assert '"ecr:GetAuthorizationToken"' in iam
    assert '"ecr:BatchGetImage"' in iam
    assert '"secretsmanager:GetSecretValue"' in iam
    assert "var.secret_arns" in iam
    assert '"secretsmanager:*"' not in iam
    assert '"ecr:*"' not in iam


def test_bootstrap_documents_ssm_registration_and_protected_environment_setup():
    guide = (ROOT / "docs/cicd/aws-github-release-foundation.md").read_text()

    assert "aws ssm describe-instance-information" in guide
    assert "production" in guide
    assert "required reviewer" in guide.lower()
    assert "aws secretsmanager put-secret-value" in guide
    assert "one-time bootstrap" in guide.lower()
