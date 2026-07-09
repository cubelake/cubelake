# Scandinavia App Store — DuckDB Queries

Пакет охватывает 4 страны: Норвегия (NO), Швеция (SE), Дания (DK), Финляндия (FI).
Данные за последние 30 дней. Продаётся как разовый срез.

---

## 0. Настройка секретов (один раз)

```sql
INSTALL azure; LOAD azure;

CREATE OR REPLACE SECRET gold_secret (
    TYPE AZURE,
    SCOPE 'azure://gold',
    CONNECTION_STRING 'AccountName=<ACCOUNT_NAME>;SharedAccessSignature=<GOLD_SAS_TOKEN>'
);
```

---

## 1. Топ-чарт по каждой стране — последний снимок

Таблица: текущий топ free/paid по всем 4 странам.

```sql
WITH latest AS (
    SELECT country, MAX(snapshot_date) AS d
    FROM read_parquet('azure://gold/fct_top_apps/snapshot_date=*/data.parquet')
    WHERE country IN ('NO', 'SE', 'DK', 'FI')
    GROUP BY country
)
SELECT
    f.country,
    f.feed_type,
    f._chart_position       AS position,
    f.app_name,
    f.developer_name,
    f.genre,
    f.rating,
    f.price,
    f.currency,
    f.snapshot_date
FROM read_parquet('azure://gold/fct_top_apps/snapshot_date=*/data.parquet') f
JOIN latest ON f.country = latest.country AND f.snapshot_date = latest.d
ORDER BY f.country, f.feed_type, f._chart_position;
```

---

## 2. Сравнение стран — топ-10 по каждой стране рядом

Удобно для side-by-side таблицы в отчёте.

```sql
WITH latest AS (
    SELECT country, MAX(snapshot_date) AS d
    FROM read_parquet('azure://gold/fct_top_apps/snapshot_date=*/data.parquet')
    WHERE country IN ('NO', 'SE', 'DK', 'FI')
    GROUP BY country
),
top10 AS (
    SELECT f.country, f.feed_type, f._chart_position AS position, f.app_name, f.developer_name, f.genre, f.rating
    FROM read_parquet('azure://gold/fct_top_apps/snapshot_date=*/data.parquet') f
    JOIN latest ON f.country = latest.country AND f.snapshot_date = latest.d
    WHERE f._chart_position <= 10
)
SELECT * FROM top10
ORDER BY feed_type, position, country;
```

---

## 3. Cross-country hits — приложения в топ-20 в 2+ странах

Самый ценный инсайт пакета: что работает по всему региону.

```sql
WITH latest AS (
    SELECT country, MAX(snapshot_date) AS d
    FROM read_parquet('azure://gold/fct_top_apps/snapshot_date=*/data.parquet')
    WHERE country IN ('NO', 'SE', 'DK', 'FI')
    GROUP BY country
),
top20 AS (
    SELECT f.app_id, f.app_name, f.developer_name, f.genre, f.country, f.feed_type, f._chart_position AS position
    FROM read_parquet('azure://gold/fct_top_apps/snapshot_date=*/data.parquet') f
    JOIN latest ON f.country = latest.country AND f.snapshot_date = latest.d
    WHERE f._chart_position <= 20
)
SELECT
    app_name,
    developer_name,
    genre,
    feed_type,
    COUNT(DISTINCT country)                                     AS countries_count,
    STRING_AGG(country || ' #' || position, ' | '
        ORDER BY position)                                      AS positions_by_country,
    ROUND(AVG(position), 1)                                     AS avg_position
FROM top20
GROUP BY app_id, app_name, developer_name, genre, feed_type
HAVING COUNT(DISTINCT country) >= 2
ORDER BY countries_count DESC, avg_position ASC;
```

---

## 4. Уникальные приложения — что есть только в одной стране

Локальные хиты, которых нет у соседей — интересно для локализации.

```sql
WITH latest AS (
    SELECT country, MAX(snapshot_date) AS d
    FROM read_parquet('azure://gold/fct_top_apps/snapshot_date=*/data.parquet')
    WHERE country IN ('NO', 'SE', 'DK', 'FI')
    GROUP BY country
),
top50 AS (
    SELECT f.app_id, f.app_name, f.developer_name, f.genre, f.country, f.feed_type, f._chart_position AS position
    FROM read_parquet('azure://gold/fct_top_apps/snapshot_date=*/data.parquet') f
    JOIN latest ON f.country = latest.country AND f.snapshot_date = latest.d
    WHERE f._chart_position <= 50
)
SELECT
    country,
    feed_type,
    position,
    app_name,
    developer_name,
    genre
FROM top50
WHERE app_id NOT IN (
    SELECT app_id FROM top50 GROUP BY app_id HAVING COUNT(DISTINCT country) > 1
)
ORDER BY country, feed_type, position;
```

---

## 5. Жанровый breakdown — сравнение стран

Какой жанр доминирует в каждой стране — видно культурные различия.

```sql
WITH latest AS (
    SELECT country, MAX(snapshot_date) AS d
    FROM read_parquet('azure://gold/fct_genre_stats/snapshot_date=*/data.parquet')
    WHERE country IN ('NO', 'SE', 'DK', 'FI')
    GROUP BY country
)
SELECT
    g.country,
    g.feed_type,
    g.genre,
    g.app_count,
    g.pct_of_chart,
    g.avg_rating,
    g.avg_price,
    g.top1_app_name
FROM read_parquet('azure://gold/fct_genre_stats/snapshot_date=*/data.parquet') g
JOIN latest ON g.country = latest.country AND g.snapshot_date = latest.d
ORDER BY g.country, g.feed_type, g.app_count DESC;
```

---

## 6. Тренд жанров по региону за 30 дней

```sql
SELECT
    g.snapshot_date,
    g.country,
    g.feed_type,
    g.genre,
    g.pct_of_chart,
    g.avg_rating,
    g.avg_price
FROM read_parquet('azure://gold/fct_genre_stats/snapshot_date=*/data.parquet') g
WHERE g.country IN ('NO', 'SE', 'DK', 'FI')
  AND g.snapshot_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY g.country, g.snapshot_date, g.feed_type, g.pct_of_chart DESC;
```

---

## 7. Растущие приложения по региону за 30 дней

```sql
SELECT
    h.country,
    h.app_name,
    h.feed_type,
    MIN(h._chart_position)              AS best_position,
    MAX(h.days_in_top)                  AS max_days_in_top,
    ROUND(AVG(h.position_delta), 1)     AS avg_daily_delta,
    SUM(CASE WHEN h.position_delta > 0 THEN 1 ELSE 0 END) AS days_rising,
    COUNT(*)                            AS days_in_chart
FROM read_parquet('azure://gold/fct_app_rank_history/data.parquet') h
WHERE h.country IN ('NO', 'SE', 'DK', 'FI')
  AND h.snapshot_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY h.country, h.app_name, h.feed_type
HAVING COUNT(*) >= 7
ORDER BY avg_daily_delta DESC
LIMIT 40;
```

---

## 8. Доминирование разработчиков по региону

Кто держит места сразу в нескольких странах.

```sql
WITH latest AS (
    SELECT country, MAX(snapshot_date) AS d
    FROM read_parquet('azure://gold/fct_top_apps/snapshot_date=*/data.parquet')
    WHERE country IN ('NO', 'SE', 'DK', 'FI')
    GROUP BY country
)
SELECT
    f.developer_name,
    f.feed_type,
    COUNT(*)                                                    AS total_slots,
    COUNT(DISTINCT f.country)                                   AS countries_present,
    COUNT(DISTINCT f.app_id)                                    AS unique_apps,
    MIN(f._chart_position)                                      AS best_position,
    ROUND(AVG(f._chart_position), 1)                           AS avg_position,
    STRING_AGG(DISTINCT f.country, ', ' ORDER BY f.country)    AS countries
FROM read_parquet('azure://gold/fct_top_apps/snapshot_date=*/data.parquet') f
JOIN latest ON f.country = latest.country AND f.snapshot_date = latest.d
GROUP BY f.developer_name, f.feed_type
ORDER BY countries_present DESC, total_slots DESC
LIMIT 25;
```

---

## Экспорт в CSV (DuckDB CLI)

```sql
COPY ( -- запрос 1 ) TO 'scandinavia_top_chart.csv'       (HEADER, DELIMITER ',');
COPY ( -- запрос 3 ) TO 'scandinavia_cross_country.csv'   (HEADER, DELIMITER ',');
COPY ( -- запрос 4 ) TO 'scandinavia_local_hits.csv'      (HEADER, DELIMITER ',');
COPY ( -- запрос 5 ) TO 'scandinavia_genre_stats.csv'     (HEADER, DELIMITER ',');
COPY ( -- запрос 7 ) TO 'scandinavia_rising_apps.csv'     (HEADER, DELIMITER ',');
COPY ( -- запрос 8 ) TO 'scandinavia_developers.csv'      (HEADER, DELIMITER ',');
```

---

## Шпаргалка

| Страна | Код | Валюта |
|--------|-----|--------|
| Норвегия | `NO` | NOK |
| Швеция | `SE` | SEK |
| Дания | `DK` | DKK |
| Финляндия | `FI` | EUR |

**Фильтр региона:** `country IN ('NO', 'SE', 'DK', 'FI')`
**30 дней:** `snapshot_date >= CURRENT_DATE - INTERVAL '30 days'`
**Position delta:** положительная = улучшение позиции
