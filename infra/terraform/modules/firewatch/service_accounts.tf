# One service account per service. Named sa-<service> so they never collide with
# the <agent>-app accounts that `agents-cli infra single-project` creates.
resource "google_service_account" "sa" {
  for_each     = toset(var.services)
  project      = var.project_id
  account_id   = "sa-${each.key}"
  display_name = "FireWatch ${each.key}"

  depends_on = [google_project_service.apis]
}
