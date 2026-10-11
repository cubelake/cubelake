variable "project_id" {
  description = "Existing GCP project, e.g. prj-d-cubelake-a1b2 (created by hand with billing attached)."
  type        = string
}

variable "env" {
  description = "Environment code used in names: d (dev) or p (prod)."
  type        = string
  validation {
    condition     = contains(["d", "p"], var.env)
    error_message = "env must be d or p."
  }
}

variable "region" {
  description = "Single region for buckets, datasets, jobs. Buckets and BigLake datasets must share it."
  type        = string
  default     = "europe-central2"
}

variable "ingest_image_tag" {
  description = "Tag of the cubelake-ingest image in Artifact Registry (git SHA, set by CD)."
  type        = string
  default     = "latest"
}

variable "github_repo_url" {
  description = "HTTPS URL of the git repo Dataform compiles from."
  type        = string
  default     = "https://github.com/Cubelake/cubelake.git"
}

variable "dataform_git_token_secret" {
  description = "Secret Manager secret id holding a read-only GitHub token for Dataform (created by hand)."
  type        = string
  default     = "dataform-github-token"
}

variable "schedule" {
  description = "Cloud Scheduler cron (UTC) for the daily pipeline."
  type        = string
  default     = "17 6 * * *"
}
