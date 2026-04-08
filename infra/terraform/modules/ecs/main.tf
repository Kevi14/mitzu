variable "environment" {}
variable "aws_region" {}
variable "backend_image_tag" {}
variable "database_url" { sensitive = true }
variable "jwt_secret" { sensitive = true }
variable "private_subnet_ids" { type = list(string) }
variable "ecs_sg_id" {}
variable "alb_target_group_arn" {}
variable "task_execution_role_arn" {}

resource "aws_ecr_repository" "backend" {
  name                 = "mitzu-backend"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration { scan_on_push = true }
}

resource "aws_ecs_cluster" "main" {
  name = "mitzu-${var.environment}"
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/mitzu-${var.environment}/backend"
  retention_in_days = 14
}

resource "aws_ecs_task_definition" "backend" {
  family                   = "mitzu-${var.environment}-backend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = var.task_execution_role_arn

  container_definitions = jsonencode([{
    name  = "backend"
    image = "${aws_ecr_repository.backend.repository_url}:${var.backend_image_tag}"
    portMappings = [{ containerPort = 8000, protocol = "tcp" }]
    environment = [
      { name = "DATABASE_URL",      value = var.database_url },
      { name = "SYNC_DATABASE_URL", value = replace(var.database_url, "asyncpg", "psycopg2") },
      { name = "SECRET_KEY",        value = var.jwt_secret },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.backend.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:8000/api/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])
}

resource "aws_ecs_service" "backend" {
  name            = "mitzu-${var.environment}-backend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_sg_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.alb_target_group_arn
    container_name   = "backend"
    container_port   = 8000
  }
}

# Autoscaling
resource "aws_appautoscaling_target" "ecs" {
  max_capacity       = 4
  min_capacity       = 1
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.backend.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "cpu" {
  name               = "mitzu-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70
  }
}

output "ecr_repository_url" { value = aws_ecr_repository.backend.repository_url }
