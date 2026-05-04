{{
    config(
        materialized='external',
        location='azure://gold/dim_apps/data.parquet',
        format='parquet'
    )
}}

-- SCD Type 1: latest known state per app_id across all silver snapshots.
SELECT
    app_id,
    app_name                                AS name,
    developer_name                          AS developer,
    primary_genre_name                      AS genre,
    primary_genre_id                        AS genre_id,
    CAST(price AS DECIMAL(10, 2))           AS price,
    currency,
    CAST(file_size_bytes AS BIGINT)         AS file_size_bytes,
    minimum_os_version                      AS min_os_version,
    content_advisory_rating                 AS content_rating,
    snapshot_date                           AS _ingested_at
FROM read_parquet('azure://silver/appstore/snapshot_date=*/apps.parquet')
WHERE app_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY app_id
    ORDER BY snapshot_date DESC
) = 1
ORDER BY app_id
