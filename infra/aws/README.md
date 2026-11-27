# AWS release foundation

This Terraform root provisions the one-time AWS side of the release boundary.
It does not deploy the application or configure GitHub environment reviewers.

## Inputs

Use `terraform.tfvars.example` as a starting point, but keep the working
`terraform.tfvars` untracked. The `github_repository` value must be the exact
`OWNER/REPOSITORY` string. `secret_arns` must contain only the two secret
container ARNs created by this root.

The first apply creates the ECR repository, OIDC role, instance profile, and
empty secret containers. Apply once more with the two secret ARNs so the EC2
inline policy is constrained to those exact resources. Secret versions and
values are intentionally managed outside Terraform.

`deployment_instance_arn` must be the exact ARN of the production EC2 instance.
The GitHub production role can send `AWS-RunShellScript` only to that instance;
SSM command status reads remain separate read-only permissions.

## Scope

- `ecr.tf`: private immutable repository and bounded lifecycle policy.
- `iam.tf`: GitHub OIDC production role and EC2 ECR/SSM/Secrets Manager access.
- `secrets.tf`: application and database secret containers only.

Attach `ec2_instance_profile_name` to the existing k0s host and verify it with
`aws ssm describe-instance-information` before enabling application CD. See
[`docs/cicd/aws-github-release-foundation.md`](../../docs/cicd/aws-github-release-foundation.md)
for the operator runbook and protected GitHub environment settings.
