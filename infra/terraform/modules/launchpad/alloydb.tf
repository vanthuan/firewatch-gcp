# Off by default: AlloyDB is billed while it exists. Turn on with enable_alloydb = true.
resource "random_password" "alloydb" {
  count   = var.enable_alloydb ? 1 : 0
  length  = 32
  special = false
}

resource "google_secret_manager_secret_version" "alloydb_password" {
  count       = var.enable_alloydb ? 1 : 0
  secret      = google_secret_manager_secret.s["alloydb-password"].id
  secret_data = random_password.alloydb[0].result
}

resource "google_alloydb_cluster" "main" {
  count      = var.enable_alloydb ? 1 : 0
  project    = var.project_id
  cluster_id = "launchpad"
  location   = var.region

  network_config {
    network            = google_compute_network.vpc.id
    allocated_ip_range = google_compute_global_address.psa.name
  }

  initial_user {
    user     = "postgres"
    password = random_password.alloydb[0].result
  }

  automated_backup_policy {
    location      = var.region
    backup_window = "3600s"
    enabled       = true

    weekly_schedule {
      days_of_week = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
      start_times {
        hours = 3
      }
    }

    time_based_retention {
      retention_period = "1209600s" # 14 days
    }
  }

  depends_on = [google_service_networking_connection.psa]
}

resource "google_alloydb_instance" "primary" {
  count         = var.enable_alloydb ? 1 : 0
  cluster       = google_alloydb_cluster.main[0].name
  instance_id   = "launchpad-primary"
  instance_type = "PRIMARY"

  machine_config {
    cpu_count = var.alloydb_cpu_count
  }

  database_flags = {
    "alloydb.iam_authentication" = "on"
  }
}
