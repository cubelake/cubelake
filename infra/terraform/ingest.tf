resource "google_artifact_registry_repository" "images" {
  repository_id = "cubelake"
  location      = var.region
  format        = "DOCKER"
  labels        = local.labels

  cleanup_policies {
    id     = "keep-recent"
    action = "KEEP"
    most_recent_versions {
      keep_count = 20
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_service_account" "ingest" {
  account_id   = "sa-ingest"
  display_name = "cubelake ingest (Cloud Run job)"
}

# One job, one image; the workflow passes `<source> --date D` as args per execution.
resource "google_cloud_run_v2_job" "ingest" {
  name                = "cubelake-ingest"
  location            = var.region
  deletion_protection = false
  labels              = local.labels

  template {
    task_count = 1
    template {
      service_account = google_service_account.ingest.email
      timeout         = "3600s"
      max_retries     = 1

      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}/cubelake-ingest:${var.ingest_image_tag}"
        args  = ["--help"]

        resources {
          limits = { cpu = "1", memory = "512Mi" }
        }

        env {
          name  = "APPLE_RSS_BRONZE_URI"
          value = "gs://${google_storage_bucket.bronze.name}/${local.bronze_tables.apple_rss.prefix}"
        }
        env {
          name  = "APPLE_ITUNES_BRONZE_URI"
          value = "gs://${google_storage_bucket.bronze.name}/${local.bronze_tables.apple_itunes.prefix}"
        }
        env {
          name  = "APPLE_ITUNES_TOP_APPS_TABLE"
          value = "${var.project_id}.silver_apple_rss.top_apps"
        }
      }
    }
  }

  depends_on = [google_project_service.apis]
}

# Least privilege: write raw files (re-runs overwrite a day), read the apple-rss silver table.
resource "google_storage_bucket_iam_member" "ingest_bronze" {
  bucket = google_storage_bucket.bronze.name
  role   = "roles/storage.objectUser"
  member = google_service_account.ingest.member
}

resource "google_bigquery_dataset_iam_member" "ingest_reads_rss_silver" {
  dataset_id = google_bigquery_dataset.this["silver_apple_rss"].dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = google_service_account.ingest.member
}

resource "google_project_iam_member" "ingest_jobs" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = google_service_account.ingest.member
}

# The BigLake connection's service account reads Iceberg data files in silver too.
resource "google_bigquery_connection_iam_member" "ingest_uses_lake" {
  location      = var.region
  connection_id = google_bigquery_connection.lake.connection_id
  role          = "roles/bigquery.connectionUser"
  member        = google_service_account.ingest.member
}
