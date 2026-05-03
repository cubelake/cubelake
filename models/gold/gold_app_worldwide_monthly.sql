{{
    config(
        materialized='external',
        location='azure://gold/appstore/monthly/snapshot_date={{ var("snapshot_date") }}/worldwide.parquet',
        format='parquet'
    )
}}

{% set snapshot_date = var("snapshot_date") %}

WITH silver AS (
    SELECT *
    FROM read_parquet('azure://silver/appstore/snapshot_date=*/*.parquet')
    WHERE snapshot_date BETWEEN
        CAST('{{ snapshot_date }}' AS DATE) - INTERVAL '29 days'
        AND CAST('{{ snapshot_date }}' AS DATE)
),

daily_agg AS (
    SELECT
        snapshot_date,
        app_id,
        feed_type,
        ANY_VALUE(app_name)                                                    AS app_name,
        ANY_VALUE(bundle_id)                                                   AS bundle_id,
        ANY_VALUE(developer_id)                                                AS developer_id,
        ANY_VALUE(developer_name)                                              AS developer_name,
        ANY_VALUE(primary_genre_name)                                          AS primary_genre_name,
        COUNT(DISTINCT country)                                                AS countries_in_top,
        ROUND(AVG(app_rank), 2)                                                AS avg_rank,
        MIN(app_rank)                                                           AS best_rank,
        ROUND(SUM(1.0 / app_rank), 4)                                         AS presence_score,
        MAX(user_rating_count)                                                  AS user_rating_count,
        ROUND(AVG(average_user_rating), 2)                                     AS avg_user_rating,
        ROUND(AVG(CASE WHEN price > 0 THEN price END), 2)                     AS avg_price_paid,
        MAX(file_size_bytes)                                                    AS file_size_bytes,
        MIN(release_date)                                                       AS release_date
    FROM silver
    GROUP BY snapshot_date, app_id, feed_type
)

SELECT
    CAST('{{ snapshot_date }}' AS DATE)                       AS snapshot_date,
    CAST('{{ snapshot_date }}' AS DATE) - INTERVAL '29 days'  AS window_start,
    CAST('{{ snapshot_date }}' AS DATE)                       AS window_end,
    30                                                         AS window_days,

    app_id,
    ANY_VALUE(app_name)                                        AS app_name,
    ANY_VALUE(bundle_id)                                       AS bundle_id,
    ANY_VALUE(developer_id)                                    AS developer_id,
    ANY_VALUE(developer_name)                                  AS developer_name,
    ANY_VALUE(primary_genre_name)                              AS primary_genre_name,
    feed_type,

    COUNT(DISTINCT snapshot_date)                              AS snapshots_available,
    ROUND(AVG(countries_in_top), 2)                           AS avg_countries_per_day,
    MAX(countries_in_top)                                      AS peak_countries_in_top,

    ROUND(AVG(avg_rank), 2)                                    AS avg_rank_worldwide,
    MIN(best_rank)                                             AS best_rank_worldwide,
    ROUND(MAX(avg_rank), 2)                                    AS worst_avg_rank_worldwide,

    ROUND(AVG(presence_score), 4)                             AS avg_presence_score,
    ROUND(MAX(presence_score), 4)                             AS peak_presence_score,

    COUNT(DISTINCT snapshot_date) FILTER (WHERE best_rank <= 10)  AS days_in_top_10,
    COUNT(DISTINCT snapshot_date) FILTER (WHERE best_rank <= 50)  AS days_in_top_50,
    COUNT(DISTINCT snapshot_date) FILTER (WHERE best_rank <= 200) AS days_in_top_200,

    ROUND(AVG(avg_user_rating), 2)                            AS avg_user_rating,
    MAX(user_rating_count)                                     AS user_rating_count,
    ROUND(AVG(avg_price_paid), 2)                             AS avg_price_paid,

    ROUND(MAX(file_size_bytes) / 1024.0 / 1024.0, 2)         AS file_size_mb,

    DATE_DIFF(
        'day',
        MIN(release_date)::DATE,
        CAST('{{ snapshot_date }}' AS DATE)
    )                                                          AS app_age_days,

    CURRENT_TIMESTAMP                                          AS _loaded_at

FROM daily_agg
GROUP BY app_id, feed_type
