# AWS/GitHub release foundation

This document covers the **one-time bootstrap** for the production release
boundary. It is intentionally separate from application CD: the release
workflow must consume these resources, not create or modify them.

## AWS bootstrap

The declarative resources live in [`infra/aws`](../../infra/aws/). Copy
`terraform.tfvars.example` to a private, untracked `terraform.tfvars`, replace
the region and repository name, and review the plan before applying:

```sh
cd infra/aws
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform fmt -check
terraform validate
terraform plan
terraform apply
```

The module creates:

- an encrypted, private, immutable ECR repository with push scanning;
- a lifecycle policy retaining the newest 20 `sha-*` release images and
  expiring untagged manifests after one day;
- the GitHub Actions OIDC provider and a production role;
- an EC2 role/instance profile with SSM managed-instance permissions, ECR
  pull permissions, and narrowly scoped Secrets Manager reads;
- empty application and database Secrets Manager containers.

No secret values are represented in Terraform. After the first apply, add the
two output ARNs to `secret_arns` in the private tfvars file and apply again.
Populate the containers through an approved operator channel without printing
values:

```sh
aws secretsmanager put-secret-value \
  --secret-id "$(terraform output -raw application_secret_arn)" \
  --secret-string '<value supplied by the operator>'
```

The command above is illustrative only; do not put the value in shell history
or CI logs. Prefer an interactive or managed secret-entry workflow. The
repository deliberately does not output secret values or create secret
versions.

## SSM registration

The EC2 host must already be registered as an SSM managed instance before CD is
enabled. An operator must:

1. attach the generated instance profile (or the existing role named by
   `ec2_instance_role_name`) to the EC2 instance;
2. install and start the regional Amazon SSM Agent using the AWS-supported
   package for the host OS;
3. provide outbound HTTPS access to SSM, EC2 Messages, and SSM Messages
   endpoints (or the approved VPC endpoints); and
4. verify registration without exposing credentials:

```sh
aws ssm describe-instance-information \
  --filters "Key=InstanceIds,Values=<EC2_INSTANCE_ID>"
```

Do not use SSH keys for release transport. The GitHub role sends a bounded SSM
command to the registered instance; the host retrieves its own secrets.

## Protected GitHub production environment

Create an environment named exactly `production` in repository settings and
configure:

- at least one **required reviewer**;
- branch/tag restriction to `main`;
- no deployment secrets containing AWS access keys or SSH private keys;
- an environment variable containing the Terraform output
  `github_production_role_arn` if the release workflow needs it.

The AWS trust policy accepts only these GitHub OIDC subjects:

- `repo:OWNER/REPOSITORY:ref:refs/heads/main`
- `repo:OWNER/REPOSITORY:environment:production`

Replace `OWNER/REPOSITORY` only in the private Terraform variables and GitHub
settings. Do not broaden the trust policy to arbitrary branches, pull
requests, or environments.

Environment protection is a GitHub repository control and cannot be safely
created by the application CD workflow itself. Record reviewer changes in the
repository administration audit trail.

## Separation and rollback boundary

This bootstrap does not run migrations, deploy Kubernetes manifests, issue
certificates, or change security groups. Application CD remains responsible for
using the immutable ECR digest through SSM. ECR retention preserves the
rollback window; a failed application rollout must not reverse a successful
database migration.
