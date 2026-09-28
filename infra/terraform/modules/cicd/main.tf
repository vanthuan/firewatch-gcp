# Single-project CI/CD (option B): path-filtered PR checks per component and
# push-to-main deploys, all running as sa-cloudbuild. No staging or prod split.
terraform {
  required_version = ">= 1.8"
  required_providers {
    google = { source = "hashicorp/google", version = ">= 6.0, < 8.0" }
  }
}

resource "google_service_account" "cloudbuild" {
  project      = var.project_id
  account_id   = "sa-cloudbuild"
  display_name = "LaunchPad Cloud Build"
}

locals {
  cloudbuild_roles = [
    "roles/logging.logWriter",         # build logs (CLOUD_LOGGING_ONLY)
    "roles/aiplatform.user",           # integration tests + Agent Runtime deploys
    "roles/storage.admin",             # Agent Runtime staging bucket, Cloud Run sources, TF state
    "roles/artifactregistry.writer",   # Cloud Run images
    "roles/cloudbuild.builds.builder", # Cloud Run source deploys start a build
    "roles/run.developer",             # Cloud Run deploys
    "roles/serviceusage.serviceUsageConsumer",
    "roles/viewer",               # terraform plan: read resources
    "roles/iam.securityReviewer", # terraform plan: read IAM policies
  ]
  sa_member = google_service_account.cloudbuild.member
  sa_id     = google_service_account.cloudbuild.id
}

resource "google_project_iam_member" "cloudbuild" {
  for_each = toset(local.cloudbuild_roles)
  project  = var.project_id
  role     = each.value
  member   = local.sa_member
}

# Deploys set each agent's runtime identity, which needs actAs on that account only.
resource "google_service_account_iam_member" "act_as_runtime" {
  for_each           = toset(distinct([for a in var.agents : a.runtime_sa]))
  service_account_id = "projects/${var.project_id}/serviceAccounts/${each.value}"
  role               = "roles/iam.serviceAccountUser"
  member             = local.sa_member
}

# ---- Agents: PR checks and deploys, one pair per folder ----
resource "google_cloudbuild_trigger" "agent_pr" {
  for_each        = var.agents
  project         = var.project_id
  location        = var.region
  name            = "pr-${each.key}"
  description     = "PR checks for agents/${each.key}"
  service_account = local.sa_id
  filename        = "cloudbuild/agent-pr.yaml"
  included_files  = ["agents/${each.key}/**", "packages/shared-py/**", "skills/**", "pyproject.toml", "uv.lock", "cloudbuild/agent-pr.yaml"]
  substitutions   = { _SERVICE = each.key }

  repository_event_config {
    repository = var.repository_id
    pull_request {
      branch          = "^${var.branch}$"
      comment_control = "COMMENTS_ENABLED_FOR_EXTERNAL_CONTRIBUTORS_ONLY"
    }
  }
}

resource "google_cloudbuild_trigger" "agent_deploy" {
  for_each        = var.agents
  project         = var.project_id
  location        = var.region
  name            = "deploy-${each.key}"
  description     = "Deploy agents/${each.key} on push to ${var.branch}"
  service_account = local.sa_id
  filename        = "cloudbuild/agent-deploy.yaml"
  disabled        = !each.value.deploy
  included_files  = ["agents/${each.key}/**", "packages/shared-py/**", "skills/**"]
  substitutions = {
    _SERVICE     = each.key
    _REGION      = var.region
    _RUNTIME_SA  = each.value.runtime_sa
    _LOGS_BUCKET = each.value.logs_bucket
  }

  repository_event_config {
    repository = var.repository_id
    push {
      branch = "^${var.branch}$"
    }
  }
}

# ---- Web, infra, Firestore rules: PR checks ----
locals {
  component_prs = {
    web       = { file = "cloudbuild/web-pr.yaml", paths = ["apps/web/**", "packages/shared-ts/**", "cloudbuild/web-pr.yaml"] }
    infra     = { file = "cloudbuild/infra-pr.yaml", paths = ["infra/**", "cloudbuild/**"] }
    firestore = { file = "cloudbuild/firestore-pr.yaml", paths = ["firestore/**", "firebase.json", "cloudbuild/firestore-pr.yaml"] }
  }
}

resource "google_cloudbuild_trigger" "component_pr" {
  for_each        = local.component_prs
  project         = var.project_id
  location        = var.region
  name            = "pr-${each.key}"
  description     = "PR checks for ${each.key}"
  service_account = local.sa_id
  filename        = each.value.file
  included_files  = each.value.paths

  repository_event_config {
    repository = var.repository_id
    pull_request {
      branch          = "^${var.branch}$"
      comment_control = "COMMENTS_ENABLED_FOR_EXTERNAL_CONTRIBUTORS_ONLY"
    }
  }
}
