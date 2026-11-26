output "ecr_repository_url" {
  description = "Private ECR repository URL used by CI and the EC2 host."
  value       = aws_ecr_repository.application.repository_url
}

output "github_production_role_arn" {
  description = "IAM role ARN configured as the GitHub Actions production role."
  value       = aws_iam_role.github_production.arn
}

output "ec2_instance_profile_name" {
  description = "Instance profile attached to the k0s EC2 host."
  value       = aws_iam_instance_profile.ec2.name
}

output "secret_arns" {
  description = "Secret container ARNs to pass back as secret_arns on a subsequent plan."
  value = {
    application = aws_secretsmanager_secret.application.arn
    database    = aws_secretsmanager_secret.database.arn
  }
}

output "application_secret_arn" {
  description = "Application secret container ARN."
  value       = aws_secretsmanager_secret.application.arn
}

output "database_secret_arn" {
  description = "Database secret container ARN."
  value       = aws_secretsmanager_secret.database.arn
}
