variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "us-east1"
}

variable "vector_backend" {
  description = "alloydb (AlloyDB + pgvector) or vertex (Vector Search, Step 4.3)"
  type        = string
  default     = "alloydb"
  validation {
    condition     = contains(["alloydb", "vertex"], var.vector_backend)
    error_message = "vector_backend must be \"alloydb\" or \"vertex\"."
  }
}

variable "services" {
  description = "Services that get their own service account sa-<name>"
  type        = list(string)
}

variable "enable_alloydb" {
  description = "Create the AlloyDB cluster and primary instance"
  type        = bool
  default     = false
}

variable "search_location" {
  description = "Vertex AI Search location: global, us or eu"
  type        = string
  default     = "global"
}

variable "subnet_cidr" {
  type    = string
  default = "10.10.0.0/24"
}

variable "alloydb_cpu_count" {
  type    = number
  default = 2
}
