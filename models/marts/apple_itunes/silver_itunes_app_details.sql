{{
    config(
        materialized='external',
        location='azure://silver/appstore_itunes/snapshot_date={{ var("snapshot_date") }}/app_details.parquet',
        format='parquet'
    )
}}

SELECT
    snapshot_date,
    CAST(UPPER(NULLIF(TRIM(country), '')) AS VARCHAR)           AS country,
    CASE
        WHEN _feed_type LIKE '%paid%' THEN 'paid'
        WHEN _feed_type LIKE '%free%' THEN 'free'
    END                                                         AS feed_type,

    r.trackId                                                   AS app_id,
    NULLIF(TRIM(r.trackName), '')                               AS app_name,
    NULLIF(TRIM(r.bundleId), '')                                AS bundle_id,
    r.artistId                                                  AS developer_id,
    NULLIF(TRIM(r.artistName), '')                              AS developer_name,
    NULLIF(TRIM(r.sellerName), '')                              AS seller_name,
    r.primaryGenreId                                            AS primary_genre_id,
    NULLIF(TRIM(r.primaryGenreName), '')                        AS primary_genre_name,
    r.genres,

    CAST(r.price AS DECIMAL(10, 2))                             AS price,
    CAST(UPPER(NULLIF(TRIM(r.currency), '')) AS VARCHAR(3))     AS currency,

    NULLIF(TRIM(r.version), '')                                 AS version,
    NULLIF(TRIM(r.minimumOsVersion), '')                        AS minimum_os_version,
    r.fileSizeBytes                                             AS file_size_bytes,
    NULLIF(TRIM(r.contentAdvisoryRating), '')                   AS content_advisory_rating,

    TRY_CAST(r.releaseDate AS TIMESTAMP)                        AS release_date,
    TRY_CAST(r.currentVersionReleaseDate AS TIMESTAMP)          AS current_version_release_date,

    CAST(r.averageUserRating AS DECIMAL(4, 2))                  AS average_user_rating,
    r.userRatingCount                                           AS user_rating_count,
    CAST(r.averageUserRatingForCurrentVersion AS DECIMAL(4, 2)) AS average_rating_current_version,
    r.userRatingCountForCurrentVersion                          AS rating_count_current_version,

    NULLIF(TRIM(r.description), '')                             AS description,
    NULLIF(TRIM(r.releaseNotes), '')                            AS release_notes,
    NULLIF(TRIM(r.artworkUrl100), '')                           AS artwork_url,
    NULLIF(TRIM(r.trackViewUrl), '')                            AS track_view_url,
    r.languageCodesISO2A                                        AS language_codes,
    r.advisories,
    r.screenshotUrls                                            AS screenshot_urls,
    r.ipadScreenshotUrls                                        AS ipad_screenshot_urls,

    TRY_CAST(_ingested_at AS TIMESTAMPTZ)                       AS ingested_at,
    CURRENT_TIMESTAMP                                           AS _loaded_at
FROM {{ ref('stg_bronze_itunes') }}
