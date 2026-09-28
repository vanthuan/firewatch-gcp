variable "project_id" {
  description = "Google Cloud project for the dev environment"
  type        = string
}

variable "region" {
  description = "Default region"
  type        = string
  default     = "us-east1"
}

variable "enable_alloydb" {
  description = "Create the AlloyDB cluster (billed while it exists; local dev uses the pgvector container)"
  type        = bool
  default     = false
}
