locals {
  topics = ["ingest-requests", "dispatch-requests"]
}

resource "google_pubsub_topic" "main" {
  for_each   = toset(local.topics)
  project    = var.project_id
  name       = each.key
  depends_on = [google_project_service.apis]
}

resource "google_pubsub_topic" "dlq" {
  for_each   = toset(local.topics)
  project    = var.project_id
  name       = "${each.key}-dlq"
  depends_on = [google_project_service.apis]
}

# Pull subscriptions for now; the workers switch them to push when they exist (Steps 2.5, 3.8).
resource "google_pubsub_subscription" "main" {
  for_each             = toset(local.topics)
  project              = var.project_id
  name                 = "${each.key}-sub"
  topic                = google_pubsub_topic.main[each.key].id
  ack_deadline_seconds = 60

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dlq[each.key].id
    max_delivery_attempts = 5
  }

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
}

# Keeps dead-lettered messages so they can be inspected and replayed.
resource "google_pubsub_subscription" "dlq" {
  for_each                   = toset(local.topics)
  project                    = var.project_id
  name                       = "${each.key}-dlq-sub"
  topic                      = google_pubsub_topic.dlq[each.key].id
  message_retention_duration = "604800s"
}

# The Pub/Sub service agent must be able to forward to the DLQ and ack the source.
resource "google_project_service_identity" "pubsub" {
  provider   = google-beta
  project    = var.project_id
  service    = "pubsub.googleapis.com"
  depends_on = [google_project_service.apis]
}

resource "google_pubsub_topic_iam_member" "dlq_publisher" {
  for_each = toset(local.topics)
  project  = var.project_id
  topic    = google_pubsub_topic.dlq[each.key].name
  role     = "roles/pubsub.publisher"
  member   = "serviceAccount:${google_project_service_identity.pubsub.email}"
}

resource "google_pubsub_subscription_iam_member" "dlq_subscriber" {
  for_each     = toset(local.topics)
  project      = var.project_id
  subscription = google_pubsub_subscription.main[each.key].name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:${google_project_service_identity.pubsub.email}"
}
