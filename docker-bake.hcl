// docker-bake.hcl - BuildKit HCL file for optimized Docker builds

// Define variables with default values
variable "TAG" {
  default = "latest"
}

variable "REGISTRY" {
  default = ""
}

// Base target with common settings
target "docker-metadata-action" {
  tags = ["${REGISTRY}foreflight-dashboard:${TAG}"]
}

// Development target
target "dev" {
  inherits = ["docker-metadata-action"]
  context = "."
  dockerfile = "Dockerfile"
  target = "development"
  tags = ["${REGISTRY}foreflight-dashboard:${TAG}-dev"]
  output = ["type=docker"]
}

// Production target
target "prod" {
  inherits = ["docker-metadata-action"]
  context = "."
  dockerfile = "Dockerfile"
  target = "production"
  tags = ["${REGISTRY}foreflight-dashboard:${TAG}"]
  output = ["type=docker"]
}

// Default target group
group "default" {
  targets = ["dev"]
}

// All targets group
group "all" {
  targets = ["dev", "prod"]
}
