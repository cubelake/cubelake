locals {
  datasets = {
    bronze_apple_rss    = { layer = "bronze", description = "Raw Apple RSS top charts (BigLake external tables over the bronze bucket)." }
    bronze_apple_itunes = { layer = "bronze", description = "Raw iTunes lookup responses (BigLake external tables over the bronze bucket)." }
    silver_apple_rss    = { layer = "silver", description = "Normalized Apple RSS charts (Iceberg managed tables)." }
    silver_apple_itunes = { layer = "silver", description = "Normalized iTunes app metadata (Iceberg managed tables)." }
    dataform_assertions = { layer = "ops", description = "Dataform assertion views (data quality checks)." }
  }

  # Raw tables: one BigLake table per source, hive partition snapshot_date (DATE).
  bronze_tables = {
    apple_rss = {
      dataset     = "bronze_apple_rss", table = "top_charts", prefix = "apple_rss/top_charts",
      schema      = "schemas/bronze_apple_rss_top_charts.json",
      description = "Apple RSS charts as returned by the API, one NDJSON file per country and feed."
    }
    apple_itunes = {
      dataset     = "bronze_apple_itunes", table = "lookup", prefix = "apple_itunes/lookup",
      schema      = "schemas/bronze_apple_itunes_lookup.json",
      description = "iTunes lookup responses for charted apps, one NDJSON file per country and feed."
    }
  }
}

resource "google_bigquery_dataset" "this" {
  for_each    = local.datasets
  dataset_id  = each.key
  location    = var.region
  description = each.value.description
  labels      = merge(local.labels, { layer = each.value.layer })

  depends_on = [google_project_service.apis]
}

# Cloud resource connection: BigLake reads the bronze bucket and Iceberg tables write the silver bucket
# through its service account, so users and jobs never need direct bucket access.
resource "google_bigquery_connection" "lake" {
  connection_id = "lake"
  location      = var.region
  friendly_name = "cubelake lake access"
  cloud_resource {}

  depends_on = [google_project_service.apis]
}

# Dataform creates Iceberg tables `WITH CONNECTION DEFAULT`: make `lake` the project default for the region.
resource "google_bigquery_job" "default_connection" {
  job_id   = "set-default-connection-${local.suffix}-${substr(sha1(google_bigquery_connection.lake.name), 0, 8)}"
  location = var.region

  query {
    query              = "ALTER PROJECT `${var.project_id}` SET OPTIONS (`region-${var.region}.default_cloud_resource_connection_id` = '${google_bigquery_connection.lake.connection_id}')"
    use_legacy_sql     = false
    create_disposition = ""
    write_disposition  = ""
  }
}

resource "google_bigquery_table" "bronze" {
  for_each            = local.bronze_tables
  dataset_id          = google_bigquery_dataset.this[each.value.dataset].dataset_id
  table_id            = each.value.table
  description         = each.value.description
  labels              = merge(local.labels, { layer = "bronze", source = each.key })
  deletion_protection = true
  max_staleness       = "0-0 0 4:0:0" # BigLake metadata cache, refreshed automatically

  external_data_configuration {
    source_format         = "NEWLINE_DELIMITED_JSON"
    source_uris           = ["gs://${google_storage_bucket.bronze.name}/${each.value.prefix}/*"]
    connection_id         = google_bigquery_connection.lake.name
    autodetect            = false
    ignore_unknown_values = true
    metadata_cache_mode   = "AUTOMATIC"
    schema                = file("${path.module}/${each.value.schema}")

    hive_partitioning_options {
      mode                     = "CUSTOM"
      source_uri_prefix        = "gs://${google_storage_bucket.bronze.name}/${each.value.prefix}/{snapshot_date:DATE}"
      require_partition_filter = true
    }
  }
}
