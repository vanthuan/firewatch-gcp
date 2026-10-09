# Single-project CI/CD (Step 1.12, option B). The GitHub connection and repository
# link were created once in the console (Cloud Build > Repositories, 2nd gen).
locals {
  sa        = module.firewatch.service_accounts
  artifacts = module.firewatch.buckets["artifacts"]
}

module "cicd" {
  source        = "../../modules/cicd"
  project_id    = var.project_id
  region        = var.region
  repository_id = "projects/${var.project_id}/locations/${var.region}/connections/github-firewatch/repositories/vanthuan-firewatch-gcp"

  agents = {
    # Keeps the identity and bucket the agents-cli Terraform gave this engine (Step 1.5).
    orchestrator = {
      runtime_sa  = "orchestrator-app@${var.project_id}.iam.gserviceaccount.com"
      logs_bucket = "${var.project_id}-orchestrator-logs"
      deploy      = true
    }
    # Deploy triggers stay off until each agent's first manual `agents-cli deploy`
    # (CI runs with --update-only). Flip to true afterwards.
    advisor         = { runtime_sa = local.sa["advisor"], logs_bucket = local.artifacts, deploy = false }
    researcher      = { runtime_sa = local.sa["researcher"], logs_bucket = local.artifacts, deploy = false }
    judge           = { runtime_sa = local.sa["judge"], logs_bucket = local.artifacts, deploy = false }
    "media-matcher" = { runtime_sa = local.sa["matcher"], logs_bucket = local.artifacts, deploy = false }
  }
}
