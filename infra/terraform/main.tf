locals {
  # Bucket names are public and global: short code + env + random suffix, no project name (GCS best practices).
  suffix        = random_id.suffix.hex
  bronze_bucket = "cbl-${var.env}-bronze-${local.suffix}"
  silver_bucket = "cbl-${var.env}-silver-${local.suffix}"
  labels        = { app = "cubelake", env = var.env == "p" ? "prod" : "dev" }
}

resource "random_id" "suffix" {
  byte_length = 2
}

resource "google_project_service" "apis" {
  for_each = toset([
    "artifactregistry.googleapis.com",
    "bigquery.googleapis.com",
    "bigqueryconnection.googleapis.com",
    "cloudscheduler.googleapis.com",
    "dataform.googleapis.com",
    "iam.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "storage.googleapis.com",
    "workflows.googleapis.com",
  ])
  service            = each.value
  disable_on_destroy = false
}
