{{
    config(
        materialized='external',
        location='{{ uri("gold") }}/fct_top_apps/snapshot_date={{ var("snapshot_date") }}/data.parquet',
        format='parquet'
    )
}}

SELECT
    snapshot_date,
    country,
    feed_type,
    app_id,
    app_name,
    developer_name,
    primary_genre_name                          AS genre,
    app_rank                                    AS _chart_position,
    CAST(average_user_rating AS DECIMAL(4, 2))  AS rating,
    CAST(price AS DECIMAL(10, 2))               AS price,
    currency,
    CURRENT_TIMESTAMP                           AS _ingested_at
FROM read_parquet('{{ uri("silver") }}/snapshot_date={{ var("snapshot_date") }}/apps.parquet')
WHERE app_id IS NOT NULL
ORDER BY country, feed_type, app_rank
