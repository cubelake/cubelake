{{
    config(
        materialized='external',
        location='{{ uri("silver") }}/snapshot_date={{ var("snapshot_date") }}/apps.parquet',
        format='parquet'
    )
}}

SELECT
    rss.snapshot_date,
    rss.country,
    rss.feed_type,
    rss.app_rank,
    rss.snapshot_updated,

    rss.app_id,
    rss.app_name,
    rss.developer_name,
    rss.track_view_url,
    rss.artwork_url,
    rss.release_date,

    itunes.bundle_id,
    itunes.developer_id,
    itunes.seller_name,
    itunes.primary_genre_id,
    itunes.primary_genre_name,
    itunes.genres,

    itunes.price,
    itunes.currency,

    itunes.version,
    itunes.minimum_os_version,
    itunes.file_size_bytes,
    itunes.content_advisory_rating,
    itunes.current_version_release_date,

    itunes.average_user_rating,
    itunes.user_rating_count,
    itunes.average_rating_current_version,
    itunes.rating_count_current_version,

    itunes.description,
    itunes.release_notes,
    itunes.language_codes,
    itunes.advisories,
    itunes.screenshot_urls,
    itunes.ipad_screenshot_urls,

    CURRENT_TIMESTAMP AS _loaded_at
FROM read_parquet('{{ uri("rss_silver") }}/snapshot_date={{ var("snapshot_date") }}/*.parquet') AS rss
LEFT JOIN read_parquet('{{ uri("itunes_silver") }}/snapshot_date={{ var("snapshot_date") }}/*.parquet') AS itunes
    ON  rss.app_id        = itunes.app_id
    AND rss.country       = itunes.country
    AND rss.snapshot_date = itunes.snapshot_date
