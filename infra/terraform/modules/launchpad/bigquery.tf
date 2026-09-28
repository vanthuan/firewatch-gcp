resource "google_bigquery_dataset" "ds" {
  for_each   = toset(["agent_analytics", "launchpad", "billing_export"])
  project    = var.project_id
  dataset_id = each.key
  location   = var.region

  depends_on = [google_project_service.apis]
}
