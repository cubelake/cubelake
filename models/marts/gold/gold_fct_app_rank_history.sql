{{
    config(
        materialized='external',
        location='azure://gold/fct_app_rank_history/data.parquet',
        format='parquet'
    )
}}

-- Full recompute: reads all silver snapshots and derives position delta + consecutive days streak.
-- position_delta > 0 means rank improved (e.g. went from #50 → #3, delta = +47).
WITH base AS (
    SELECT
        app_id,
        app_name,
        country,
        feed_type,
        snapshot_date,
        app_rank AS _chart_position
    FROM read_parquet('azure://silver/appstore/snapshot_date=*/apps.parquet')
    WHERE app_id IS NOT NULL
),
with_lag AS (
    SELECT
        *,
        LAG(_chart_position) OVER w AS prev_position,
        LAG(snapshot_date)   OVER w AS prev_date
    FROM base
    WINDOW w AS (PARTITION BY app_id, country, feed_type ORDER BY snapshot_date)
),
-- gaps-and-islands: increment streak_group whenever there is a gap (app was absent yesterday)
with_streak_group AS (
    SELECT
        *,
        SUM(
            CASE WHEN prev_date IS NULL OR prev_date < snapshot_date - INTERVAL '1 day'
                 THEN 1 ELSE 0 END
        ) OVER (
            PARTITION BY app_id, country, feed_type
            ORDER BY snapshot_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS streak_group
    FROM with_lag
)
SELECT
    app_id,
    app_name,
    country,
    feed_type,
    snapshot_date,
    _chart_position,
    prev_position,
    CASE WHEN prev_position IS NULL THEN NULL
         ELSE prev_position - _chart_position
    END AS position_delta,
    ROW_NUMBER() OVER (
        PARTITION BY app_id, country, feed_type, streak_group
        ORDER BY snapshot_date
    ) AS days_in_top,
    CURRENT_TIMESTAMP AS _ingested_at
FROM with_streak_group
ORDER BY country, feed_type, snapshot_date, _chart_position
