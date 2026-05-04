{{
    config(
        materialized='external',
        location='azure://gold/fct_genre_stats/snapshot_date={{ var("snapshot_date") }}/data.parquet',
        format='parquet'
    )
}}

WITH base AS (
    SELECT
        snapshot_date,
        country,
        feed_type,
        primary_genre_name  AS genre,
        app_id,
        app_name,
        app_rank,
        average_user_rating AS rating,
        price
    FROM read_parquet('azure://silver/appstore/snapshot_date={{ var("snapshot_date") }}/apps.parquet')
    WHERE app_id IS NOT NULL
      AND primary_genre_name IS NOT NULL
),
genre_leader AS (
    SELECT snapshot_date, country, feed_type, genre, app_id AS top1_app_id, app_name AS top1_app_name
    FROM base
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY snapshot_date, country, feed_type, genre
        ORDER BY app_rank
    ) = 1
),
genre_stats AS (
    SELECT
        snapshot_date,
        country,
        feed_type,
        genre,
        COUNT(DISTINCT app_id)          AS app_count,
        ROUND(AVG(rating), 2)           AS avg_rating,
        ROUND(AVG(price), 2)            AS avg_price
    FROM base
    GROUP BY 1, 2, 3, 4
),
totals AS (
    SELECT snapshot_date, country, feed_type, SUM(app_count) AS total_apps
    FROM genre_stats
    GROUP BY 1, 2, 3
)
SELECT
    gs.snapshot_date,
    gs.country,
    gs.feed_type,
    gs.genre,
    gs.app_count,
    gs.avg_rating,
    gs.avg_price,
    ROUND(gs.app_count * 100.0 / t.total_apps, 2)  AS pct_of_chart,
    gl.top1_app_id,
    gl.top1_app_name,
    CURRENT_TIMESTAMP                               AS _ingested_at
FROM genre_stats gs
JOIN genre_leader gl USING (snapshot_date, country, feed_type, genre)
JOIN totals t       USING (snapshot_date, country, feed_type)
ORDER BY gs.country, gs.feed_type, gs.app_count DESC
