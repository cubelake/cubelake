resource "google_service_account" "dataform" {
  account_id   = "sa-dataform"
  display_name = "cubelake Dataform runs"
}

data "google_secret_manager_secret_version" "dataform_git_token" {
  secret = var.dataform_git_token_secret
}

resource "google_dataform_repository" "cubelake" {
  provider        = google-beta
  name            = "cubelake"
  region          = var.region
  service_account = google_service_account.dataform.email

  git_remote_settings {
    url                                 = var.github_repo_url
    default_branch                      = "main"
    authentication_token_secret_version = data.google_secret_manager_secret_version.dataform_git_token.name
  }

  depends_on = [google_project_service.apis]
}

# The Dataform service agent only exists after it is provisioned; IAM bindings below fail without it.
resource "google_project_service_identity" "dataform" {
  provider = google-beta
  service  = "dataform.googleapis.com"

  depends_on = [google_project_service.apis]
}

locals {
  dataform_agent = "serviceAccount:${google_project_service_identity.dataform.email}"
}

# Dataform's service agent reads the git token and acts as sa-dataform (strict act-as).
resource "google_secret_manager_secret_iam_member" "dataform_agent_token" {
  secret_id = var.dataform_git_token_secret
  role      = "roles/secretmanager.secretAccessor"
  member    = local.dataform_agent
}

resource "google_service_account_iam_member" "dataform_agent_actas" {
  service_account_id = google_service_account.dataform.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = local.dataform_agent
}

# sa-dataform: read bronze, write silver + assertions, create Iceberg tables via the lake connection.
resource "google_bigquery_dataset_iam_member" "dataform_reads_bronze" {
  for_each   = toset(["bronze_apple_rss", "bronze_apple_itunes"])
  dataset_id = google_bigquery_dataset.this[each.key].dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = google_service_account.dataform.member
}

resource "google_bigquery_dataset_iam_member" "dataform_writes" {
  for_each   = toset(["silver_apple_rss", "silver_apple_itunes", "dataform_assertions"])
  dataset_id = google_bigquery_dataset.this[each.key].dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = google_service_account.dataform.member
}

resource "google_project_iam_member" "dataform_jobs" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = google_service_account.dataform.member
}

resource "google_bigquery_connection_iam_member" "dataform_delegates_lake" {
  location      = var.region
  connection_id = google_bigquery_connection.lake.connection_id
  role          = "roles/bigquery.connectionAdmin" # includes connections.delegate, needed to create Iceberg tables
  member        = google_service_account.dataform.member
}

# The connection's own service account does the actual file I/O.
resource "google_storage_bucket_iam_member" "lake_reads_bronze" {
  bucket = google_storage_bucket.bronze.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_bigquery_connection.lake.cloud_resource[0].service_account_id}"
}

resource "google_storage_bucket_iam_member" "lake_writes_silver" {
  bucket = google_storage_bucket.silver.name
  role   = "roles/storage.objectUser"
  member = "serviceAccount:${google_bigquery_connection.lake.cloud_resource[0].service_account_id}"
}
