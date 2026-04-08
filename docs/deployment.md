# AWS Deployment Plan

## Architecture Overview

```
Internet
    │
    ▼
[ALB — HTTPS/443]
    │ forward all traffic
    ▼
[ECS Fargate Task — FastAPI]
  ├── serves /api/* (FastAPI routes)
  └── serves /*    (React SPA via StaticFiles)
    │
    ▼
[RDS PostgreSQL 16 — private subnet]
```

The frontend is **built into the backend Docker image** (multi-stage build). FastAPI mounts
`dist/` at `/` via `StaticFiles`. No S3 or CloudFront required — one container handles
everything. This simplifies the Terraform to 4 modules instead of 6.

---

## AWS Services

| Service | Purpose | Config |
|---|---|---|
| **VPC** | Isolated network | 2 public + 2 private subnets across 2 AZs |
| **ALB** | TLS termination + routing | HTTPS 443 → ECS, HTTP 80 → redirect |
| **ACM** | TLS certificate | DNS-validated, auto-renewed |
| **ECS Fargate** | Container runtime (stateless) | 1 vCPU / 2 GB, 1–4 tasks (CPU autoscaling at 70%) |
| **ECR** | Docker image registry | Scan-on-push enabled |
| **RDS PostgreSQL 16** | Persistent data store | db.t3.medium, 100 GB gp3, 7-day PITR |
| **NAT Gateway** | Outbound internet for private subnets | Single AZ (cost vs. HA tradeoff) |
| **IAM** | ECS task execution role | ECR pull + CloudWatch logs |
| **CloudWatch Logs** | Container logs | `/ecs/mitzu-prod/backend`, 14-day retention |
| **SSM Parameter Store** | Secrets (not in image) | `jwt_secret`, `db_password` |

---

## Tradeoffs

### Single-AZ NAT Gateway
A single NAT Gateway costs ~$32/month vs ~$64 for two. For a demo/small-scale deployment this
is acceptable. Production with availability requirements should add a second NAT in the other AZ.

### RDS `db.t3.medium` (not Multi-AZ)
Multi-AZ doubles the RDS cost. For a demo or non-critical analytics workload, single-AZ with
7-day PITR is sufficient. Promote to Multi-AZ when RTO < 1 minute is required.

### ECS Fargate over EC2
Fargate eliminates instance management, patching, and capacity planning. The cost premium
(~20–30% over comparable EC2) is worth it at this scale.

### No CDN for Frontend
Since the React build is served by FastAPI directly, there's no edge caching. For a global
audience, adding CloudFront in front of the ALB (caching `/assets/*` with long TTLs) would
reduce latency and ALB costs without any code changes.

### Ingestion in Web Process
Data ingestion runs in the web worker via `run_in_executor`. At scale, this should move to a
separate ECS task (triggered by an EventBridge rule or SQS message) to avoid blocking the API.

---

## Deployment Steps

```bash
# 1. Configure Terraform backend (one-time)
# Create an S3 bucket + DynamoDB table, then update main.tf backend block.

# 2. Build and push image
aws ecr get-login-password | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
docker build -t mitzu-backend .
docker tag mitzu-backend:latest <ecr-url>:latest
docker push <ecr-url>:latest

# 3. Apply Terraform
cd infra/terraform
terraform init
terraform plan -var="db_password=..." -var="jwt_secret=..."
terraform apply

# 4. Run database migrations (one-time, via ECS exec or bastion)
# aws ecs execute-command --cluster mitzu-prod --task <task-id> \
#   --container backend --interactive \
#   --command "uv run alembic upgrade head"
```

---

## Cost Estimate (us-east-1, ~730 hrs/month)

| Resource | Monthly cost |
|---|---|
| ECS Fargate (1 task, 1 vCPU / 2 GB) | ~$30 |
| RDS db.t3.medium (single-AZ) | ~$70 |
| ALB | ~$18 |
| NAT Gateway | ~$32 |
| ECR storage | ~$1 |
| CloudWatch Logs | ~$2 |
| **Total** | **~$153/month** |
