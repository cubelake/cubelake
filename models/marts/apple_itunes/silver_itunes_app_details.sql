{{
    config(
        materialized='external',
        location='azure://silver/appstore_itunes/snapshot_date={{ var("snapshot_date") }}/app_details.parquet',
        format='parquet'
    )
}}

SELECT
    CAST(r.trackId AS VARCHAR)                                     AS app_id,
    NULLIF(trim(r.trackName), '')                                  AS app_name,
    NULLIF(trim(r.artistName), '')                                 AS app_developer,
    NULLIF(trim(r.bundleId), '')                                   AS bundle_id,
    NULLIF(trim(r.primaryGenreName), '')                           AS primary_genre,
    r.genres                                                       AS genres,
    CAST(UPPER(NULLIF(trim(country), '')) AS VARCHAR)              AS country,
    CASE
        WHEN _feed_type LIKE '%paid%' THEN 'paid'
        WHEN _feed_type LIKE '%free%' THEN 'free'
    END                                                            AS feed_type,
    CAST(r.price AS DOUBLE)                                        AS price,
    NULLIF(trim(r.formattedPrice), '')                             AS formatted_price,
    CAST(r.averageUserRating AS DOUBLE)                            AS avg_rating,
    CAST(r.userRatingCount AS INTEGER)                             AS rating_count,
    TRY_CAST(r.releaseDate AS TIMESTAMP)                           AS release_date,
    TRY_CAST(r.currentVersionReleaseDate AS TIMESTAMP)             AS current_version_release_date,
    NULLIF(trim(r.version), '')                                    AS app_version,
    NULLIF(trim(r.trackViewUrl), '')                               AS app_url,
    NULLIF(trim(r.artworkUrl512), '')                              AS app_image_url,
    CURRENT_TIMESTAMP                                              AS _loaded_at
FROM {{ ref('stg_bronze_itunes') }}
