resource "aws_secretsmanager_secret" "application" {
  name                    = var.production_secret_names.application
  description             = "Japp production application secret values; populated out-of-band."
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret" "database" {
  name                    = var.production_secret_names.database
  description             = "Japp production database secret values; populated out-of-band."
  recovery_window_in_days = 7
}
