resource "google_service_account" "workflows" {
  account_id   = "sa-workflows"
  display_name = "cubelake daily workflow"
}

resource "google_workflows_workflow" "daily" {
  name            = "cubelake-daily"
  region          = var.region
  description     = "raw → silver for every source: extract job, then Dataform per source tag."
  service_account = google_service_account.workflows.email
  source_contents = file("${path.module}/../../workflows/cubelake-daily.yaml")
  labels          = local.labels
  call_log_level  = "LOG_ERRORS_ONLY"

  user_env_vars = {
    REGION              = var.region
    EXTRACT_JOB         = google_cloud_run_v2_job.extract.name
    DATAFORM_REPOSITORY = google_dataform_repository.cubelake.id
    SILVER_BUCKET       = google_storage_bucket.silver.name
  }

  depends_on = [google_project_service.apis]
}

# Run the extract job with per-execution args (runWithOverrides is in run.developer), scoped to the job.
resource "google_cloud_run_v2_job_iam_member" "workflows_runs_extract" {
  name     = google_cloud_run_v2_job.extract.name
  location = var.region
  role     = "roles/run.developer"
  member   = google_service_account.workflows.member
}

resource "google_service_account_iam_member" "workflows_actas_extract" {
  service_account_id = google_service_account.extract.name
  role               = "roles/iam.serviceAccountUser"
  member             = google_service_account.workflows.member
}

resource "google_project_iam_member" "workflows" {
  for_each = toset(["roles/dataform.editor", "roles/logging.logWriter", "roles/workflows.invoker"])
  project  = var.project_id
  role     = each.value
  member   = google_service_account.workflows.member
}

resource "google_service_account_iam_member" "workflows_actas_dataform" {
  service_account_id = google_service_account.dataform.name
  role               = "roles/iam.serviceAccountUser"
  member             = google_service_account.workflows.member
}

resource "google_cloud_scheduler_job" "daily" {
  name        = "cubelake-daily"
  region      = var.region
  description = "Starts the cubelake-daily workflow for today's snapshot."
  schedule    = var.schedule
  time_zone   = "Etc/UTC"

  retry_config {
    retry_count = 1
  }

  http_target {
    http_method = "POST"
    uri         = "https://workflowexecutions.googleapis.com/v1/${google_workflows_workflow.daily.id}/executions"
    body        = base64encode(jsonencode({ argument = jsonencode({}) }))

    oauth_token {
      service_account_email = google_service_account.workflows.email
      scope                 = "https://www.googleapis.com/auth/cloud-platform"
    }
  }

  depends_on = [google_project_service.apis]
}
