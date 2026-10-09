output "service_accounts" {
  value = { for k, sa in google_service_account.sa : k => sa.email }
}

output "buckets" {
  value = { for k, b in google_storage_bucket.b : k => b.name }
}

output "topics" {
  value = { for k, t in google_pubsub_topic.main : k => t.name }
}

output "subscriptions" {
  value = { for k, s in google_pubsub_subscription.main : k => s.name }
}

output "network" {
  value = {
    vpc    = google_compute_network.vpc.name
    subnet = google_compute_subnetwork.main.name
  }
}

output "alloydb_instance" {
  value = var.enable_alloydb ? google_alloydb_instance.primary[0].name : null
}

output "search" {
  description = "Datastore IDs for VertexAiSearchTool(data_store_id=...) and app IDs for the console"
  value = {
    catalog_datastore = google_discovery_engine_data_store.catalog.name
    kb_datastore      = google_discovery_engine_data_store.kb.name
    catalog_app       = google_discovery_engine_search_engine.catalog.engine_id
    kb_app            = google_discovery_engine_search_engine.kb.engine_id
  }
}

output "vector_backend" {
  value = var.vector_backend
}
