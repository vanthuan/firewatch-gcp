# Vertex AI Search (Step 2.3). Datastores live in a multi-region (global/us/eu), not us-east1.
#   catalog: structured products, imported from gs://{project}-artifacts/catalog/products.jsonl
#   kb:      unstructured briefs and docs, layout parser with table + image annotation, chunked
# Each datastore gets a search app (engine): the console's Preview tab lives on apps.

resource "google_discovery_engine_data_store" "catalog" {
  project           = var.project_id
  location          = var.search_location
  data_store_id     = "catalog"
  display_name      = "LaunchPad product catalog"
  industry_vertical = "GENERIC"
  solution_types    = ["SOLUTION_TYPE_SEARCH"]
  content_config    = "NO_CONTENT" # structured rows only

  depends_on = [google_project_service.apis]
}

resource "google_discovery_engine_data_store" "kb" {
  project           = var.project_id
  location          = var.search_location
  data_store_id     = "kb"
  display_name      = "LaunchPad knowledge base"
  industry_vertical = "GENERIC"
  solution_types    = ["SOLUTION_TYPE_SEARCH"]
  content_config    = "CONTENT_REQUIRED" # PDFs, images, HTML

  document_processing_config {
    default_parsing_config {
      layout_parsing_config {
        enable_table_annotation = true # Gemini describes tables
        enable_image_annotation = true # Gemini describes images (swatches, charts)
      }
    }
    chunking_config {
      layout_based_chunking_config {
        chunk_size                = 500
        include_ancestor_headings = true
      }
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_discovery_engine_search_engine" "catalog" {
  project           = var.project_id
  location          = var.search_location
  collection_id     = "default_collection"
  engine_id         = "catalog-search"
  display_name      = "LaunchPad catalog search"
  industry_vertical = "GENERIC"
  data_store_ids    = [google_discovery_engine_data_store.catalog.data_store_id]

  search_engine_config {
    search_tier = "SEARCH_TIER_STANDARD"
  }
}

resource "google_discovery_engine_search_engine" "kb" {
  project           = var.project_id
  location          = var.search_location
  collection_id     = "default_collection"
  engine_id         = "kb-search"
  display_name      = "LaunchPad knowledge search"
  industry_vertical = "GENERIC"
  data_store_ids    = [google_discovery_engine_data_store.kb.data_store_id]

  search_engine_config {
    search_tier = "SEARCH_TIER_ENTERPRISE" # extractive segments for [doc, page] citations
  }
}

# Imports from GCS run as the Discovery Engine service agent, which needs to read the source buckets.
resource "google_project_service_identity" "discoveryengine" {
  provider   = google-beta
  project    = var.project_id
  service    = "discoveryengine.googleapis.com"
  depends_on = [google_project_service.apis]
}

resource "google_storage_bucket_iam_member" "discoveryengine_read" {
  for_each = toset(["artifacts", "briefs", "kb"])
  bucket   = google_storage_bucket.b[each.key].name
  role     = "roles/storage.objectViewer"
  member   = "serviceAccount:${google_project_service_identity.discoveryengine.email}"
}
