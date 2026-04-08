variable "environment" {}
variable "db_password" { sensitive = true }
variable "private_subnet_ids" { type = list(string) }
variable "rds_sg_id" {}

resource "aws_db_subnet_group" "main" {
  name       = "mitzu-${var.environment}"
  subnet_ids = var.private_subnet_ids
}

resource "aws_db_instance" "main" {
  identifier             = "mitzu-${var.environment}"
  engine                 = "postgres"
  engine_version         = "16"
  instance_class         = "db.t3.medium"
  allocated_storage      = 100
  storage_type           = "gp3"
  db_name                = "mitzu"
  username               = "mitzu"
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [var.rds_sg_id]
  skip_final_snapshot    = false
  final_snapshot_identifier = "mitzu-${var.environment}-final"
  backup_retention_period = 7
  deletion_protection    = true

  tags = { Name = "mitzu-${var.environment}-rds" }
}

output "endpoint"     { value = aws_db_instance.main.endpoint sensitive = true }
output "database_url" {
  value     = "postgresql+asyncpg://mitzu:${var.db_password}@${aws_db_instance.main.endpoint}/mitzu"
  sensitive = true
}
