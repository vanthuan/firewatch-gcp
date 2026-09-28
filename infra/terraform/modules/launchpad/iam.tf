# Least-privilege roles per service. Bindings for services not in var.services are skipped.
# run.invoker on researcher/judge/media_matcher is added once those services exist (Step 3.2).
locals {
  project_roles = {
    web          = ["roles/aiplatform.user", "roles/datastore.user"]
    orchestrator = ["roles/aiplatform.user", "roles/datastore.user", "roles/discoveryengine.viewer"]
    advisor      = ["roles/aiplatform.user", "roles/discoveryengine.viewer"]
    researcher   = ["roles/aiplatform.user"]
    judge        = ["roles/aiplatform.user"]
    matcher      = ["roles/aiplatform.user", "roles/alloydb.client", "roles/alloydb.databaseUser", "roles/serviceusage.serviceUsageConsumer"]
    ingest       = ["roles/aiplatform.user", "roles/datastore.user", "roles/discoveryengine.editor", "roles/modelarmor.user"]
    dispatch     = ["roles/datastore.user"]
    backfill     = ["roles/aiplatform.user", "roles/alloydb.client", "roles/alloydb.databaseUser", "roles/serviceusage.serviceUsageConsumer"]
  }

  project_bindings = {
    for pair in flatten([
      for svc, roles in local.project_roles : [
        for role in roles : { svc = svc, role = role }
      ] if contains(var.services, svc)
    ]) : "${pair.svc}:${pair.role}" => pair
  }

  bucket_bindings = {
    for b in [
      { svc = "web", bucket = "briefs", role = "roles/storage.objectCreator" },
      { svc = "web", bucket = "assets", role = "roles/storage.objectViewer" },
      { svc = "ingest", bucket = "briefs", role = "roles/storage.objectViewer" },
      { svc = "ingest", bucket = "kb", role = "roles/storage.objectAdmin" },
      { svc = "orchestrator", bucket = "artifacts", role = "roles/storage.objectAdmin" },
      { svc = "orchestrator", bucket = "skills", role = "roles/storage.objectViewer" },
      { svc = "advisor", bucket = "assets", role = "roles/storage.objectViewer" },
    ] : "${b.svc}:${b.bucket}:${b.role}" => b if contains(var.services, b.svc)
  }

  secret_bindings = {
    for s in ["matcher", "backfill"] : s => s if contains(var.services, s)
  }

  topic_bindings = {
    for b in [
      { svc = "orchestrator", topic = "dispatch-requests", kind = "publisher" },
      { svc = "web", topic = "dispatch-requests", kind = "publisher" },
      { svc = "dispatch", topic = "dispatch-requests", kind = "subscriber" },
      { svc = "ingest", topic = "ingest-requests", kind = "subscriber" },
    ] : "${b.svc}:${b.topic}:${b.kind}" => b if contains(var.services, b.svc)
  }
}

resource "google_project_iam_member" "sa" {
  for_each = local.project_bindings
  project  = var.project_id
  role     = each.value.role
  member   = google_service_account.sa[each.value.svc].member
}

resource "google_storage_bucket_iam_member" "sa" {
  for_each = local.bucket_bindings
  bucket   = google_storage_bucket.b[each.value.bucket].name
  role     = each.value.role
  member   = google_service_account.sa[each.value.svc].member
}

resource "google_secret_manager_secret_iam_member" "alloydb_password" {
  for_each  = local.secret_bindings
  project   = var.project_id
  secret_id = google_secret_manager_secret.s["alloydb-password"].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = google_service_account.sa[each.key].member
}

resource "google_pubsub_topic_iam_member" "publisher" {
  for_each = { for k, b in local.topic_bindings : k => b if b.kind == "publisher" }
  project  = var.project_id
  topic    = google_pubsub_topic.main[each.value.topic].name
  role     = "roles/pubsub.publisher"
  member   = google_service_account.sa[each.value.svc].member
}

resource "google_pubsub_subscription_iam_member" "subscriber" {
  for_each     = { for k, b in local.topic_bindings : k => b if b.kind == "subscriber" }
  project      = var.project_id
  subscription = google_pubsub_subscription.main[each.value.topic].name
  role         = "roles/pubsub.subscriber"
  member       = google_service_account.sa[each.value.svc].member
}

# The web BFF signs upload URLs with its own identity (Step 2.4).
resource "google_service_account_iam_member" "web_sign_blob" {
  count              = contains(var.services, "web") ? 1 : 0
  service_account_id = google_service_account.sa["web"].name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = google_service_account.sa["web"].member
}
