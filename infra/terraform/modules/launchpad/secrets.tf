# Secret containers only. alloydb-password gets a version from alloydb.tf;
# gateway-api-key is added by hand once the send provider exists.
resource "google_secret_manager_secret" "s" {
  for_each  = toset(["alloydb-password", "gateway-api-key"])
  project   = var.project_id
  secret_id = each.key

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}
