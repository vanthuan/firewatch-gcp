# infra/terraform/envs/dev/main.tf
module "firewatch" {
  source         = "../../modules/firewatch"
  project_id     = var.project_id
  region         = var.region
  vector_backend = "alloydb"
  enable_alloydb = var.enable_alloydb
  services       = ["web", "orchestrator", "advisor", "researcher", "judge", "matcher", "ingest", "dispatch", "backfill"]
}
