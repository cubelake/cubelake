terraform {
  required_version = ">= 1.9"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # State bucket is created once by hand (see README): terraform init -backend-config="bucket=<state-bucket>"
  backend "gcs" {
    prefix = "cubelake"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Dataform repositories are only in the beta provider.
provider "google-beta" {
  project = var.project_id
  region  = var.region
}
