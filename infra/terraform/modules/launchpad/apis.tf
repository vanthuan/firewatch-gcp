locals {
  apis = [
    "aiplatform.googleapis.com",
    "run.googleapis.com",
    "firestore.googleapis.com",
    "alloydb.googleapis.com",
    "storage.googleapis.com",
    "secretmanager.googleapis.com",
    "pubsub.googleapis.com",
    "cloudtasks.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "modelarmor.googleapis.com",
    "identitytoolkit.googleapis.com",
    "bigquery.googleapis.com",
    "discoveryengine.googleapis.com",
    "servicenetworking.googleapis.com",
    "vpcaccess.googleapis.com",
    "compute.googleapis.com",
    "iam.googleapis.com",
    "cloudresourcemanager.googleapis.com",
  ]
}

resource "google_project_service" "apis" {
  for_each           = toset(local.apis)
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false # shared with the agents-cli Terraform
}
