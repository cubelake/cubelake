output "bronze_bucket" {
  value = google_storage_bucket.bronze.name
}

output "silver_bucket" {
  value = google_storage_bucket.silver.name
}

output "ingest_image" {
  description = "Push the ingest image here (tag = git SHA)."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}/cubelake-ingest"
}

output "workflow" {
  value = google_workflows_workflow.daily.id
}
