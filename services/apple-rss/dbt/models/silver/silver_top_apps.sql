{{
    config(
        materialized='external',
        location='{{ uri("silver") }}/snapshot_date={{ var("snapshot_date") }}/top_apps.parquet',
        format='parquet'
    )
}}

SELECT
    CAST('{{ var("snapshot_date") }}' AS DATE)                    AS snapshot_date,
    CAST(row_number AS INTEGER)                                   AS app_rank,
    CAST(UPPER(NULLIF(TRIM(country), '')) AS VARCHAR)             AS country,
    CASE
        WHEN _feed_type LIKE '%paid%' THEN 'paid'
        WHEN _feed_type LIKE '%free%' THEN 'free'
    END                                                           AS feed_type,
    try_strptime(updated, '%a, %d %b %Y %H:%M:%S %z')             AS snapshot_updated,
    CURRENT_TIMESTAMP                                             AS _loaded_at,
    TRY_CAST(NULLIF(trim(r.id), '') AS BIGINT)                    AS app_id,
    NULLIF(trim(r.name), '')                                      AS app_name,
    NULLIF(trim(r.artistName), '')                                AS developer_name,
    NULLIF(trim(r.url), '')                                       AS track_view_url,
    NULLIF(trim(r.artworkUrl100), '')                             AS artwork_url,
    TRY_CAST(r.releaseDate AS TIMESTAMP)                          AS release_date
FROM {{ ref('stg_bronze_top_apps') }}
