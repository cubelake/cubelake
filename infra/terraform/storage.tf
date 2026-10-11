# Raw zone: API responses as NDJSON, hive-partitioned by snapshot_date. Kept forever, versioned.
resource "google_storage_bucket" "bronze" {
  name                        = local.bronze_bucket
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  labels                      = merge(local.labels, { layer = "bronze" })

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition { age = 90 }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }
  lifecycle_rule {
    condition {
      days_since_noncurrent_time = 30
    }
    action { type = "Delete" }
  }

  depends_on = [google_project_service.apis]
}

# Silver: Iceberg managed tables written by BigQuery (data under iceberg/<dataset>/<table>/).
# Only BigQuery writes here — never edit files by hand.
resource "google_storage_bucket" "silver" {
  name                        = local.silver_bucket
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  labels                      = merge(local.labels, { layer = "silver" })

  depends_on = [google_project_service.apis]
}
