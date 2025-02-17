module "option_system" {
  source  = "terraform-aws-modules/ecs/aws"
  version = "~> 4.0"
  
  cluster_name = "option-cluster"
  fargate_capacity_providers = ["FARGATE"]
  
  services = {
    option-system = {
      cpu    = 1024
      memory = 2048
      container_definitions = [{
        name  = "option-system"
        image = "registry.example.com/option-system:${var.image_tag}"
        portMappings = [{ containerPort = 8000 }]
      }]
    }
  }
  
  tags = {
    Environment = "prod"
  }
} 