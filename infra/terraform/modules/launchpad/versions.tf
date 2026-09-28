terraform {
  required_version = ">= 1.8"
  required_providers {
    google      = { source = "hashicorp/google", version = ">= 6.0, < 8.0" }
    google-beta = { source = "hashicorp/google-beta", version = ">= 6.0, < 8.0" }
    random      = { source = "hashicorp/random", version = ">= 3.6" }
  }
}

data "google_project" "this" {
  project_id = var.project_id
}
