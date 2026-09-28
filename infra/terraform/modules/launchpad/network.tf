resource "google_compute_network" "vpc" {
  project                 = var.project_id
  name                    = "launchpad-vpc"
  auto_create_subnetworks = false
  depends_on              = [google_project_service.apis]
}

# Cloud Run services/jobs attach here with Direct VPC egress (Step 1.7).
resource "google_compute_subnetwork" "main" {
  project                  = var.project_id
  name                     = "launchpad-${var.region}"
  region                   = var.region
  network                  = google_compute_network.vpc.id
  ip_cidr_range            = var.subnet_cidr
  private_ip_google_access = true
}

# Private Services Access range used by AlloyDB.
resource "google_compute_global_address" "psa" {
  project       = var.project_id
  name          = "launchpad-psa"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
}

resource "google_service_networking_connection" "psa" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.psa.name]
}

resource "google_compute_router" "router" {
  project = var.project_id
  name    = "launchpad-router"
  region  = var.region
  network = google_compute_network.vpc.id
}

resource "google_compute_router_nat" "nat" {
  project                            = var.project_id
  name                               = "launchpad-nat"
  router                             = google_compute_router.router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}

# From the subnet, only Postgres ports may reach the AlloyDB range:
# 5432 for direct connections, 5433 for the AlloyDB connectors and Auth Proxy.
resource "google_compute_firewall" "alloydb_allow" {
  project            = var.project_id
  name               = "launchpad-egress-alloydb-postgres"
  network            = google_compute_network.vpc.id
  direction          = "EGRESS"
  priority           = 1000
  destination_ranges = ["${google_compute_global_address.psa.address}/${google_compute_global_address.psa.prefix_length}"]
  allow {
    protocol = "tcp"
    ports    = ["5432", "5433"]
  }
}

resource "google_compute_firewall" "alloydb_deny_rest" {
  project            = var.project_id
  name               = "launchpad-egress-alloydb-deny-other"
  network            = google_compute_network.vpc.id
  direction          = "EGRESS"
  priority           = 1100
  destination_ranges = ["${google_compute_global_address.psa.address}/${google_compute_global_address.psa.prefix_length}"]
  deny {
    protocol = "all"
  }
}
