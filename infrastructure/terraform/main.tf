###############################################################################
# LLMOps Gateway AI - AWS Infrastructure (Terraform)
# Provisions: EKS, RDS PostgreSQL, ElastiCache Redis, ECR, VPC
###############################################################################

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
  }

  # Store state in S3 with DynamoDB locking
  backend "s3" {
    bucket         = "llmops-terraform-state"
    key            = "llmops-gateway-ai/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "llmops-terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = "llmops-gateway-ai"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

###############################################################################
# VPC
###############################################################################

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "llmops-vpc-${var.environment}"
  cidr = "10.0.0.0/16"

  azs             = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway   = true
  single_nat_gateway   = var.environment != "production"
  enable_dns_hostnames = true
  enable_dns_support   = true

  public_subnet_tags = {
    "kubernetes.io/role/elb" = 1
  }
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = 1
  }
}

###############################################################################
# ECR - Container Registry
###############################################################################

resource "aws_ecr_repository" "llmops" {
  name                 = "llmops-gateway-ai"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }
}

resource "aws_ecr_lifecycle_policy" "llmops" {
  repository = aws_ecr_repository.llmops.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 10 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}

###############################################################################
# EKS Cluster
###############################################################################

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = "llmops-cluster-${var.environment}"
  cluster_version = "1.28"

  vpc_id                         = module.vpc.vpc_id
  subnet_ids                     = module.vpc.private_subnets
  cluster_endpoint_public_access = true

  cluster_addons = {
    coredns            = { most_recent = true }
    kube-proxy         = { most_recent = true }
    vpc-cni            = { most_recent = true }
    aws-ebs-csi-driver = { most_recent = true }
  }

  eks_managed_node_groups = {
    # General purpose nodes
    general = {
      name           = "general-${var.environment}"
      instance_types = ["t3.medium"]
      min_size       = 2
      max_size       = 10
      desired_size   = 3

      labels = {
        role = "general"
      }
    }

    # GPU nodes for embedding models (optional)
    gpu = {
      name           = "gpu-${var.environment}"
      instance_types = ["g4dn.xlarge"]
      min_size       = 0
      max_size       = 3
      desired_size   = 0

      labels = {
        role = "gpu"
      }
      taints = [{
        key    = "nvidia.com/gpu"
        value  = "true"
        effect = "NO_SCHEDULE"
      }]
    }
  }
}

###############################################################################
# RDS PostgreSQL
###############################################################################

module "rds" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 6.0"

  identifier = "llmops-postgres-${var.environment}"

  engine               = "postgres"
  engine_version       = "16.1"
  instance_class       = var.environment == "production" ? "db.t3.medium" : "db.t3.micro"
  allocated_storage    = 20
  max_allocated_storage = 100

  db_name  = "llmops_db"
  username = "llmops"
  manage_master_user_password = true  # Stores in AWS Secrets Manager

  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.llmops.name

  backup_retention_period = var.environment == "production" ? 7 : 1
  deletion_protection     = var.environment == "production"
  skip_final_snapshot     = var.environment != "production"

  parameters = [
    { name = "log_connections", value = "1" },
    { name = "log_min_duration_statement", value = "1000" },
  ]
}

resource "aws_db_subnet_group" "llmops" {
  name       = "llmops-db-subnet-group"
  subnet_ids = module.vpc.private_subnets
}

###############################################################################
# ElastiCache Redis
###############################################################################

resource "aws_elasticache_subnet_group" "llmops" {
  name       = "llmops-redis-subnet"
  subnet_ids = module.vpc.private_subnets
}

resource "aws_elasticache_replication_group" "llmops" {
  replication_group_id = "llmops-redis-${var.environment}"
  description          = "LLMOps Gateway Redis cache"

  node_type            = "cache.t3.micro"
  num_cache_clusters   = var.environment == "production" ? 2 : 1
  parameter_group_name = "default.redis7"
  port                 = 6379

  subnet_group_name  = aws_elasticache_subnet_group.llmops.name
  security_group_ids = [aws_security_group.redis.id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true

  automatic_failover_enabled = var.environment == "production"
}

###############################################################################
# Security Groups
###############################################################################

resource "aws_security_group" "rds" {
  name_prefix = "llmops-rds-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [module.eks.node_security_group_id]
  }
}

resource "aws_security_group" "redis" {
  name_prefix = "llmops-redis-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [module.eks.node_security_group_id]
  }
}

###############################################################################
# Secrets Manager
###############################################################################

resource "aws_secretsmanager_secret" "llmops_secrets" {
  name                    = "llmops-gateway-ai/${var.environment}/app-secrets"
  recovery_window_in_days = 7
}

###############################################################################
# CloudWatch Log Group
###############################################################################

resource "aws_cloudwatch_log_group" "llmops" {
  name              = "/llmops-gateway-ai/${var.environment}"
  retention_in_days = 30
}

###############################################################################
# IAM Role for EKS Service Account (IRSA)
###############################################################################

module "llmops_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.0"

  role_name = "llmops-gateway-role"

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["llmops:llmops-sa"]
    }
  }

  role_policy_arns = {
    secretsmanager = aws_iam_policy.secretsmanager.arn
    cloudwatch     = aws_iam_policy.cloudwatch.arn
  }
}

resource "aws_iam_policy" "secretsmanager" {
  name = "llmops-secretsmanager-policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"]
      Resource = aws_secretsmanager_secret.llmops_secrets.arn
    }]
  })
}

resource "aws_iam_policy" "cloudwatch" {
  name = "llmops-cloudwatch-policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = "${aws_cloudwatch_log_group.llmops.arn}:*"
    }]
  })
}

###############################################################################
# Outputs
###############################################################################

output "eks_cluster_name" {
  value = module.eks.cluster_name
}

output "ecr_repository_url" {
  value = aws_ecr_repository.llmops.repository_url
}

output "rds_endpoint" {
  value     = module.rds.db_instance_endpoint
  sensitive = true
}

output "redis_endpoint" {
  value     = aws_elasticache_replication_group.llmops.primary_endpoint_address
  sensitive = true
}
