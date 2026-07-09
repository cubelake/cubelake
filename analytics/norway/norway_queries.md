# Norway App Store — DuckDB Queries

Запросы для анализа норвежского рынка. Данные за последние 30 дней.
Все читают напрямую из ADLS Parquet через wildcard-пути.

---

## 0. Настройка секретов (один раз перед запросами)

```sql
INSTALL azure; LOAD azure;

CREATE OR REPLACE SECRET gold_secret (
    TYPE AZURE,
    SCOPE 'azure://gold',
    CONNECTION_STRING 'AccountName=<ACCOUNT_NAME>;SharedAccessSignature=<GOLD_SAS_TOKEN>'
);
```

---

## 1. Топ-чарт Норвегии — последний снимок

Используется для таблицы в Metabase: текущий топ free/paid с рейтингом и ценой.

```sql
WITH latest AS (
    SELECT MAX(snapshot_date) AS d
    FROM read_parquet('azure://gold/fct_top_apps/snapshot_date=*/data.parquet')
    WHERE country = 'NO'
)
SELECT
    f.feed_type,
    f._chart_position                   AS position,
    f.app_name,
    f.developer_name,
    f.genre,
    f.rating,
    f.price,
    f.currency,
    f.snapshot_date
FROM read_parquet('azure://gold/fct_top_apps/snapshot_date=*/data.parquet') f
CROSS JOIN latest
WHERE f.country = 'NO'
  AND f.snapshot_date = latest.d
ORDER BY f.feed_type, f._chart_position;
```

**Metabase:** Table chart, фильтр по `feed_type`. Колонку `position` закрепить первой.

---

## 2. Тренд позиций — топ-10 стабильных приложений за 30 дней

Только приложения которые провели больше всего дней в топ-10.
Остальные через топ-10 проходили случайно и только зашумляют график.

```sql
WITH consistent_apps AS (
    SELECT app_name, feed_type
    FROM read_parquet('azure://gold/fct_app_rank_history/data.parquet')
    WHERE country = 'NO'
      AND snapshot_date >= CURRENT_DATE - INTERVAL '30 days'
      AND _chart_position <= 10
    GROUP BY app_name, feed_type
    ORDER BY COUNT(*) DESC, AVG(_chart_position) ASC
    LIMIT 10
)
SELECT
    h.snapshot_date,
    h.feed_type,
    h.app_name,
    (11 - h._chart_position)            AS position,
    h.position_delta,
    h.days_in_top
FROM read_parquet('azure://gold/fct_app_rank_history/data.parquet') h
JOIN consistent_apps c
    ON h.app_name = c.app_name
   AND h.feed_type = c.feed_type
WHERE h.country = 'NO'
  AND h.snapshot_date >= CURRENT_DATE - INTERVAL '30 days'
  AND h._chart_position <= 10
ORDER BY h.feed_type, h.snapshot_date, h._chart_position;
```

**Metabase:** Line chart, X = `snapshot_date`, Y = `position` (ось инвертирована — 1 = лучше), Series = `app_name`. Фильтр по `feed_type`.

---

## 3. Самые растущие приложения за 30 дней

Кто больше всего поднялся в чарте — полезно для продажи как "rising stars".

```sql
SELECT
    h.app_name,
    h.feed_type,
    MIN(h._chart_position)              AS best_position,
    MAX(h._chart_position)              AS worst_position,
    MAX(h.days_in_top)                  AS max_days_in_top,
    ROUND(AVG(h.position_delta), 1)     AS avg_daily_delta,
    SUM(CASE WHEN h.position_delta > 0 THEN 1 ELSE 0 END) AS days_rising,
    COUNT(*)                            AS days_in_chart
FROM read_parquet('azure://gold/fct_app_rank_history/data.parquet') h
WHERE h.country = 'NO'
  AND h.snapshot_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY h.app_name, h.feed_type
HAVING COUNT(*) >= 7                    -- минимум неделя в чарте
ORDER BY avg_daily_delta DESC;
```

**Metabase:** Bar chart по `avg_daily_delta`, раскраска по `feed_type`.

---

## 4. Жанровый breakdown — последний снимок

Доля каждого жанра в норвежском чарте.

```sql
WITH latest AS (
    SELECT MAX(snapshot_date) AS d
    FROM read_parquet('azure://gold/fct_genre_stats/snapshot_date=*/data.parquet')
    WHERE country = 'NO'
)
SELECT
    g.feed_type,
    g.genre,
    g.app_count,
    g.pct_of_chart,
    g.avg_rating,
    g.avg_price,
    g.top1_app_name
FROM read_parquet('azure://gold/fct_genre_stats/snapshot_date=*/data.parquet') g
CROSS JOIN latest
WHERE g.country = 'NO'
  AND g.snapshot_date = latest.d
ORDER BY g.feed_type, g.app_count DESC;
```

**Metabase:** Pie chart или Bar chart по `pct_of_chart`, фильтр по `feed_type`.

---

## 5. Тренд жанров за 30 дней

Как менялась доля жанров со временем.

```sql
SELECT
    g.snapshot_date,
    g.feed_type,
    g.genre,
    g.app_count,
    g.pct_of_chart,
    g.avg_rating,
    g.avg_price
FROM read_parquet('azure://gold/fct_genre_stats/snapshot_date=*/data.parquet') g
WHERE g.country = 'NO'
  AND g.snapshot_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY g.snapshot_date, g.feed_type, g.app_count DESC;
```

**Metabase:** Stacked bar или Area chart, X = `snapshot_date`, Y = `pct_of_chart`, Series = `genre`.

---

## 6. Доминирование разработчиков — последний снимок

Кто держит больше всего мест в чарте.

```sql
WITH latest AS (
    SELECT MAX(snapshot_date) AS d
    FROM read_parquet('azure://gold/fct_top_apps/snapshot_date=*/data.parquet')
    WHERE country = 'NO'
)
SELECT
    f.feed_type,
    f.developer_name,
    COUNT(*)                            AS apps_in_chart,
    MIN(f._chart_position)              AS best_position,
    ROUND(AVG(f._chart_position), 1)    AS avg_position,
    ROUND(AVG(f.rating), 2)             AS avg_rating,
    STRING_AGG(f.app_name, ', '
        ORDER BY f._chart_position)     AS apps
FROM read_parquet('azure://gold/fct_top_apps/snapshot_date=*/data.parquet') f
CROSS JOIN latest
WHERE f.country = 'NO'
  AND f.snapshot_date = latest.d
GROUP BY f.feed_type, f.developer_name
ORDER BY apps_in_chart DESC, avg_position ASC;
```

**Metabase:** Bar chart по `apps_in_chart`, фильтр по `feed_type`. Колонка `apps` — tooltip.

---

## 7. Экспорт в CSV (если через DuckDB CLI)

```sql
-- Пример для топ-чарта
COPY (
    -- вставить SELECT из запроса #1
) TO 'norway_top_chart.csv' (HEADER, DELIMITER ',');
```

---

## Структура данных — шпаргалка

| Таблица | Путь в ADLS | Зерно |
|---------|------------|-------|
| `fct_top_apps` | `azure://gold/fct_top_apps/snapshot_date=*/data.parquet` | app × country × feed_type × date |
| `fct_genre_stats` | `azure://gold/fct_genre_stats/snapshot_date=*/data.parquet` | genre × country × feed_type × date |
| `fct_app_rank_history` | `azure://gold/fct_app_rank_history/data.parquet` | app × country × feed_type × date (вся история) |
| `dim_apps` | `azure://gold/dim_apps/data.parquet` | app_id (последнее состояние) |

**Norway filter:** `country = 'NO'`
**30 дней:** `snapshot_date >= CURRENT_DATE - INTERVAL '30 days'`
**Позиция delta:** положительная = улучшение (напр. с #50 на #3 → delta = +47)
