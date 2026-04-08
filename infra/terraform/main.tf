terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment and configure before running in a real environment:
  # backend "s3" {
  #   bucket         = "your-tfstate-bucket"
  #   key            = "mitzu/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "your-tfstate-lock"
  # }
}

provider "aws" {
  region = var.aws_region
}

module "networking" {
  source      = "./modules/networking"
  environment = var.environment
}

module "iam" {
  source      = "./modules/iam"
  environment = var.environment
}

module "rds" {
  source             = "./modules/rds"
  environment        = var.environment
  db_password        = var.db_password
  private_subnet_ids = module.networking.private_subnet_ids
  rds_sg_id          = module.networking.rds_sg_id
}

module "ecs" {
  source                    = "./modules/ecs"
  environment               = var.environment
  aws_region                = var.aws_region
  backend_image_tag         = var.backend_image_tag
  database_url              = module.rds.database_url
  jwt_secret                = var.jwt_secret
  private_subnet_ids        = module.networking.private_subnet_ids
  ecs_sg_id                 = module.networking.ecs_sg_id
  alb_target_group_arn      = module.alb.target_group_arn
  task_execution_role_arn   = module.iam.task_execution_role_arn
}

module "alb" {
  source            = "./modules/alb"
  environment       = var.environment
  public_subnet_ids = module.networking.public_subnet_ids
  alb_sg_id         = module.networking.alb_sg_id
  vpc_id            = module.networking.vpc_id
  domain_name       = var.domain_name
}
