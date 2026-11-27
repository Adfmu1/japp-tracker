variable "aws_region" {
  description = "AWS region containing ECR, IAM, and Secrets Manager resources."
  type        = string
}

variable "application_name" {
  description = "Lowercase application name used in AWS resource names."
  type        = string
  default     = "japp"
}

variable "github_repository" {
  description = "GitHub repository in OWNER/REPOSITORY form, without a URL."
  type        = string
}

variable "github_oidc_thumbprint" {
  description = "Public GitHub Actions OIDC root CA thumbprint."
  type        = string
  default     = "6938fd4d98bab03faadb97b34396831e3780aea1"
}

variable "ec2_instance_role_name" {
  description = "Existing EC2 role name, or the role name to create for the host."
  type        = string
  default     = null
  nullable    = true
}

variable "secret_arns" {
  description = "Exact Secrets Manager ARNs the EC2 role may read."
  type        = list(string)
  default     = []
}

variable "deployment_instance_arn" {
  description = "Exact EC2 instance ARN that the GitHub production role may target with SSM commands."
  type        = string
}

variable "production_secret_names" {
  description = "Names for the application and database secret containers. Values are never managed by Terraform."
  type = object({
    application = optional(string, "/japp/production/application")
    database    = optional(string, "/japp/production/database")
  })
  default = {}
}
