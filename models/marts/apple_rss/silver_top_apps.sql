{{
    config(
        materialized='external',
        location='azure://silver/appstore_rss/snapshot_date={{ var("snapshot_date") }}/top_apps.parquet',
        format='parquet'
    )
}}

SELECT
    CAST(row_number AS INTEGER)                                   AS app_rank,
    CAST(UPPER(NULLIF(trim(country), '')) AS VARCHAR)             AS country,
    CASE
        WHEN _feed_type LIKE '%paid%' THEN 'paid'
        WHEN _feed_type LIKE '%free%' THEN 'free'
    END                                                           AS feed_type,
    strptime(updated, '%a, %d %b %Y %H:%M:%S %z')                AS snapshot_updated,
    CURRENT_TIMESTAMP                                             AS _loaded_at,
    NULLIF(trim(r.id), '')                                        AS app_id,
    NULLIF(trim(r.name), '')                                      AS app_name,
    NULLIF(trim(r.artistName), '')                                AS app_developer,
    NULLIF(trim(r.url), '')                                       AS app_url,
    NULLIF(trim(r.artworkUrl100), '')                             AS app_image_url,
    r.releaseDate                                                 AS app_release_date
FROM {{ ref('stg_bronze_top_apps') }}
