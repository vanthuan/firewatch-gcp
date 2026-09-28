locals {
  # bucket suffix => versioning on?
  buckets = {
    briefs    = true
    kb        = false
    artifacts = false
    skills    = false
    assets    = false
  }
}

# Lifecycle and retention rules come in Step 5.8.
resource "google_storage_bucket" "b" {
  for_each                    = local.buckets
  project                     = var.project_id
  name                        = "${var.project_id}-${each.key}"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = each.value
  }

  depends_on = [google_project_service.apis]
}
