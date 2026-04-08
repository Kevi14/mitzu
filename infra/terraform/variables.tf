variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "prod"
}

variable "db_password" {
  description = "RDS postgres password"
  type        = string
  sensitive   = true
}

variable "jwt_secret" {
  description = "Secret key for JWT signing"
  type        = string
  sensitive   = true
}

variable "domain_name" {
  description = "Custom domain (e.g. mitzu.example.com)"
  type        = string
  default     = ""
}

variable "backend_image_tag" {
  description = "ECR image tag for the backend container"
  type        = string
  default     = "latest"
}
