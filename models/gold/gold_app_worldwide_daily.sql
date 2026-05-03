{{
    config(
        materialized='external',
        location='azure://gold/appstore/daily/snapshot_date={{ var("snapshot_date") }}/worldwide.parquet',
        format='parquet'
    )
}}

{% set snapshot_date = var("snapshot_date") %}
{% set prev_date = (modules.datetime.date.fromisoformat(snapshot_date) - modules.datetime.timedelta(days=1)).isoformat() %}

WITH current_day AS (
    SELECT *
    FROM read_parquet('azure://silver/appstore/snapshot_date={{ snapshot_date }}/*.parquet')
),

{% if var("has_prev_snapshot", false) %}
prev_day AS (
    SELECT
        app_id,
        feed_type,
        ROUND(AVG(app_rank), 2)        AS avg_rank,
        MIN(app_rank)                   AS best_rank,
        ROUND(SUM(1.0 / app_rank), 4)  AS presence_score,
        COUNT(DISTINCT country)         AS countries_in_top
    FROM read_parquet('azure://silver/appstore/snapshot_date={{ prev_date }}/*.parquet')
    GROUP BY app_id, feed_type
),
{% else %}
prev_day AS (
    SELECT
        NULL::BIGINT   AS app_id,
        NULL::VARCHAR  AS feed_type,
        NULL::DOUBLE   AS avg_rank,
        NULL::INTEGER  AS best_rank,
        NULL::DOUBLE   AS presence_score,
        NULL::INTEGER  AS countries_in_top
    WHERE FALSE
),
{% endif %}

aggregated AS (
    SELECT
        CAST('{{ snapshot_date }}' AS DATE)                                          AS snapshot_date,
        app_id,
        feed_type,
        ANY_VALUE(app_name)                                                           AS app_name,
        ANY_VALUE(bundle_id)                                                          AS bundle_id,
        ANY_VALUE(developer_id)                                                       AS developer_id,
        ANY_VALUE(developer_name)                                                     AS developer_name,
        ANY_VALUE(primary_genre_name)                                                 AS primary_genre_name,
        ANY_VALUE(version)                                                            AS version,
        ANY_VALUE(content_advisory_rating)                                            AS content_advisory_rating,
        ANY_VALUE(minimum_os_version)                                                 AS minimum_os_version,

        COUNT(DISTINCT country)                                                       AS countries_in_top,
        ROUND(AVG(app_rank), 2)                                                       AS avg_rank_worldwide,
        MIN(app_rank)                                                                  AS best_rank_worldwide,
        MAX(app_rank)                                                                  AS worst_rank_worldwide,
        ROUND(SUM(1.0 / app_rank), 4)                                                AS global_presence_score,

        ROUND(AVG(average_user_rating), 2)                                            AS avg_user_rating,
        MAX(user_rating_count)                                                         AS user_rating_count,

        ROUND(AVG(CASE WHEN price > 0 THEN price END), 2)                            AS avg_price_paid,
        BOOL_OR(price = 0)                                                            AS has_free_version,
        BOOL_AND(price > 0)                                                           AS is_paid_only,

        ROUND(MAX(file_size_bytes) / 1024.0 / 1024.0, 2)                            AS file_size_mb,

        DATE_DIFF('day', MIN(release_date)::DATE, CAST('{{ snapshot_date }}' AS DATE))                   AS app_age_days,
        DATE_DIFF('day', MAX(current_version_release_date)::DATE, CAST('{{ snapshot_date }}' AS DATE))   AS days_since_last_update
    FROM current_day
    GROUP BY app_id, feed_type
)

SELECT
    a.snapshot_date,
    a.app_id,
    a.app_name,
    a.bundle_id,
    a.developer_id,
    a.developer_name,
    a.primary_genre_name,
    a.version,
    a.content_advisory_rating,
    a.minimum_os_version,
    a.feed_type,

    a.countries_in_top,
    a.avg_rank_worldwide,
    a.best_rank_worldwide,
    a.worst_rank_worldwide,
    a.global_presence_score,

    p.avg_rank            AS prev_avg_rank_worldwide,
    p.best_rank           AS prev_best_rank_worldwide,
    p.presence_score      AS prev_global_presence_score,
    p.countries_in_top    AS prev_countries_in_top,

    ROUND(p.avg_rank - a.avg_rank_worldwide, 2)           AS avg_rank_change,
    ROUND(p.presence_score - a.global_presence_score, 4)  AS presence_score_change,
    CASE
        WHEN p.app_id IS NULL              THEN 'new_entry'
        WHEN a.avg_rank_worldwide < p.avg_rank THEN 'rising'
        WHEN a.avg_rank_worldwide > p.avg_rank THEN 'falling'
        ELSE 'stable'
    END                                                    AS rank_trend,

    a.avg_user_rating,
    a.user_rating_count,
    a.avg_price_paid,
    a.has_free_version,
    a.is_paid_only,
    a.file_size_mb,
    a.app_age_days,
    a.days_since_last_update,

    CURRENT_TIMESTAMP AS _loaded_at

FROM aggregated a
LEFT JOIN prev_day p USING (app_id, feed_type)
