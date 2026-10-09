terraform {
  required_version = ">= 1.8"
  required_providers {
    google      = { source = "hashicorp/google", version = ">= 6.0, < 8.0" }
    google-beta = { source = "hashicorp/google-beta", version = ">= 6.0, < 8.0" }
    random      = { source = "hashicorp/random", version = ">= 3.6" }
  }
}

# user_project_override + billing_project: bill API quota to this project. Some APIs
# (Discovery Engine, Model Armor) reject user credentials that have no quota project.
provider "google" {
  project               = var.project_id
  region                = var.region
  user_project_override = true
  billing_project       = var.project_id
}

provider "google-beta" {
  project               = var.project_id
  region                = var.region
  user_project_override = true
  billing_project       = var.project_id
}
