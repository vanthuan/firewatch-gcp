variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "us-east1"
}

variable "repository_id" {
  description = "Cloud Build 2nd-gen repository: projects/P/locations/R/connections/C/repositories/NAME"
  type        = string
}

variable "branch" {
  type    = string
  default = "main"
}

variable "agents" {
  description = <<-EOT
    One entry per folder under agents/.
    runtime_sa  = email the deployed agent runs as
    logs_bucket = value for LOGS_BUCKET_NAME
    deploy      = enable the push-to-main deploy trigger (the first deploy is manual; CI uses --update-only)
  EOT
  type = map(object({
    runtime_sa  = string
    logs_bucket = string
    deploy      = bool
  }))
}
