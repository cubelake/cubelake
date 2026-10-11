# Данные: где лежат и в каком виде

Всё находится в одном регионе — `europe-central2`. Для BigLake это обязательно: бакеты и датасеты должны
быть в одном регионе. `<env>` — `d` (dev) или `p` (prod), `<rand>` — случайный суффикс, который выдаёт
Terraform (смотрите `terraform output`).

## Карта хранения

| Что | Где | Формат | Кто пишет | Кто читает |
| --- | --- | --- | --- | --- |
| Bronze, файлы | `gs://cbl-<env>-bronze-<rand>/<source>/<dataset>/snapshot_date=YYYY-MM-DD/<country>_<feed>.json` | NDJSON, 1 строка = 1 ответ API | `sa-ingest` | BigLake (connection `lake`) |
| Bronze, таблицы | BigQuery `bronze_apple_rss.top_charts`, `bronze_apple_itunes.lookup` | BigLake external table над файлами выше | Terraform (только определение) | Dataform, аналитики |
| Silver, таблицы | BigQuery `silver_apple_rss.top_apps`, `silver_apple_itunes.app_details` | Apache Iceberg managed table | Dataform (`sa-dataform`) | `sa-ingest` (iTunes), аналитики, позже gold |
| Silver, файлы | `gs://cbl-<env>-silver-<rand>/iceberg/<dataset>/<table>/` | Parquet + метаданные Iceberg | **только BigQuery** | BigQuery, любые Iceberg-движки (Spark и др.) |
| Проверки качества | BigQuery `dataform_assertions.*` | views | Dataform | Dataform |
| Docker-образы | `europe-central2-docker.pkg.dev/<project>/cubelake/cubelake-ingest:<tag>` | OCI | вы / CD | Cloud Run |
| Terraform state | `gs://<ваш state-бакет>/cubelake/` | tfstate | Terraform | Terraform |
| GitHub-токен Dataform | Secret Manager `dataform-github-token` | секрет | вы | агент Dataform |

> Файлы в silver-бакете **никогда не правьте руками**: ими управляет BigQuery, и ручная правка сломает
> таблицу. Меняйте данные только через Dataform или SQL.

## Bronze

### Раскладка путей

```text
gs://cbl-d-bronze-7f3c/
  apple_rss/top_charts/snapshot_date=2026-10-11/
    us_top_free.json
    us_top_paid.json
    no_top_free.json
    … (175 стран × 2 фида = до 350 файлов в день)
  apple_itunes/lookup/snapshot_date=2026-10-11/
    us_top_free.json
    … (по файлу на каждый фид, который был в RSS в этот день)
```

Правила:
- `snapshot_date=YYYY-MM-DD` — это hive-партиция. BigQuery видит её как колонку `snapshot_date DATE`.
  **Внутри файлов этого поля нет и быть не должно.**
- Имя файла: `<country>_<feed>.json`, страна в нижнем регистре (`us`), фид — `top_free` или `top_paid`.
- Повторный прогон дня перезаписывает файлы этого дня. Прежние версии хранятся 30 дней, потому что у
  бакета включено версионирование.
- Bronze хранится всегда. Через 90 дней объекты переходят в класс Nearline (дешевле хранить, дороже читать).

### Формат записи

Каждый файл содержит **одну строку JSON** (NDJSON). Сначала идут служебные поля, затем ответ API как есть:

| Поле | Тип | Значение |
| --- | --- | --- |
| `_source` | string | `apple-rss` или `apple-itunes` |
| `_ingested_at` | string (ISO-8601 UTC) | когда записано |
| `_feed_type` | string | `top_free` / `top_paid` |
| `country` | string | код страны в нижнем регистре |
| … | | поля ответа API |

Apple RSS: в файл кладётся содержимое `feed` из ответа. Пример ответа: `docs/apple_rss_sample_feed.json`.

```json
{"_source": "apple-rss", "_ingested_at": "2026-10-11T06:17:42+00:00", "_feed_type": "top_free",
 "country": "us", "title": "Top Free Apps", "id": "…", "updated": "Sat, 11 Oct 2026 06:00:00 +0000",
 "results": [{"id": "6448311069", "name": "…", "artistName": "…", "releaseDate": "2023-05-18",
              "kind": "apps", "artworkUrl100": "…", "url": "…", "genres": [ … ]}, …]}
```

iTunes lookup: в файл кладётся весь ответ `https://itunes.apple.com/lookup?id=…&country=…`, то есть
`resultCount` и `results[]` с полной карточкой приложения.

Этот формат **стабилен**: на нём держатся уже собранные данные и silver-модели. Новые поля можно добавлять,
переименовывать и удалять существующие нельзя.

### Bronze-таблицы в BigQuery

| Таблица | Источник файлов | Схема |
| --- | --- | --- |
| `bronze_apple_rss.top_charts` | `apple_rss/top_charts/*` | `infra/terraform/schemas/bronze_apple_rss_top_charts.json` |
| `bronze_apple_itunes.lookup` | `apple_itunes/lookup/*` | `infra/terraform/schemas/bronze_apple_itunes_lookup.json` |

- Схема задана явно, автоопределения нет. Лишние поля из JSON игнорируются (`ignore_unknown_values`).
- **Без фильтра по `snapshot_date` запрос не выполнится** (`require_partition_filter`). Так BigQuery не
  сканирует всю историю случайно.
- Кэш метаданных BigLake обновляется автоматически, допустимая задержка — до 4 часов.

```sql
SELECT country, _feed_type, ARRAY_LENGTH(results) AS apps
FROM bronze_apple_rss.top_charts
WHERE snapshot_date = '2026-10-11';
```

## Silver

Это Iceberg managed tables: метаданные хранит BigQuery, данные лежат в нашем silver-бакете в формате
Parquet. Таблицы партиционированы по `snapshot_date` и кластеризованы по `country, feed_type`.
Загрузка инкрементальная: MERGE по ключу, поэтому повторный прогон дня безопасен.

### `silver_apple_rss.top_apps`

Одна строка на позицию в чарте: **день × страна × фид × место**. Ключ:
`(snapshot_date, country, feed_type, app_rank)`.

| Колонка | Тип | Описание |
| --- | --- | --- |
| `snapshot_date` | DATE | день сбора (партиция bronze) |
| `app_rank` | INT64 | место в чарте, 1–100 |
| `country` | STRING | ISO 3166-1 alpha-2, ВЕРХНИЙ регистр |
| `feed_type` | STRING | `free` / `paid` |
| `snapshot_updated` | TIMESTAMP | время чарта по Apple |
| `app_id` | INT64 | id в App Store (trackId) |
| `app_name`, `developer_name` | STRING | |
| `track_view_url`, `artwork_url` | STRING | |
| `release_date` | TIMESTAMP | |
| `_loaded_at` | TIMESTAMP | когда строку записал Dataform |

Проверки:
- not null: `snapshot_date`, `app_rank`, `country`, `feed_type`;
- ключ уникален;
- `feed_type ∈ {free, paid}`;
- `app_rank` от 1 до 100.

### `silver_apple_itunes.app_details`

Карточка приложения: **день × страна × фид × app_id**. Ключ: `(snapshot_date, country, feed_type, app_id)`.

| Колонка | Тип | Описание |
| --- | --- | --- |
| `snapshot_date`, `country`, `feed_type`, `app_id` | | ключ (как в `top_apps`) |
| `app_name`, `bundle_id`, `developer_id`, `developer_name`, `seller_name` | | |
| `primary_genre_id`, `primary_genre_name`, `genres` | | `genres` — массив строк |
| `price` | NUMERIC(2 знака) | в валюте `currency` |
| `currency` | STRING | ВЕРХНИЙ регистр |
| `version`, `minimum_os_version`, `file_size_bytes`, `content_advisory_rating` | | `file_size_bytes` — INT64 (iTunes присылает строку) |
| `release_date`, `current_version_release_date` | TIMESTAMP | |
| `average_user_rating`, `user_rating_count` | NUMERIC, INT64 | за всё время |
| `average_rating_current_version`, `rating_count_current_version` | NUMERIC, INT64 | для текущей версии |
| `description`, `release_notes` | STRING | |
| `artwork_url`, `track_view_url`, `language_codes`, `advisories`, `screenshot_urls`, `ipad_screenshot_urls` | | массивы — ARRAY<STRING> |
| `ingested_at` | TIMESTAMP | когда ответ лёг в bronze |
| `_loaded_at` | TIMESTAMP | когда строку записал Dataform |

Проверки:
- not null: `snapshot_date`, `country`, `feed_type`, `app_id`;
- ключ уникален;
- `feed_type ∈ {free, paid}`;
- `price` пустой или ≥ 0.

```sql
-- топ-10 бесплатных в США с рейтингом
SELECT t.app_rank, t.app_name, d.average_user_rating, d.user_rating_count
FROM silver_apple_rss.top_apps t
JOIN silver_apple_itunes.app_details d USING (snapshot_date, country, feed_type, app_id)
WHERE t.snapshot_date = '2026-10-11' AND t.country = 'US' AND t.feed_type = 'free'
ORDER BY t.app_rank LIMIT 10;
```

## Именование

| Что | Шаблон | Пример |
| --- | --- | --- |
| Проекты | `prj-<d\|p>-cubelake-<rand>` | `prj-p-cubelake-a1b2` |
| Бакеты | `cbl-<d\|p>-<bronze\|silver>-<rand>` | `cbl-p-bronze-7f3c` |
| Датасеты | `<layer>_<source>` | `silver_apple_rss` |
| Bronze-пути | `<source>/<dataset>/snapshot_date=D/<country>_<feed>.json` | `apple_rss/top_charts/snapshot_date=2026-10-11/us_top_free.json` |
| Silver-файлы | `iceberg/<dataset>/<table>/` | `iceberg/silver_apple_rss/top_apps/` |
| Файлы Dataform | `definitions/sources/<source>/<source>_<table>.sqlx` | `apple_rss_top_apps.sqlx` |
| Сервисные аккаунты | `sa-<роль>` | `sa-ingest`, `sa-dataform`, `sa-workflows` |

## Старые данные (Azure)

Bronze, собранный до перехода на GCP, лежит в Azure ADLS Gen2 по путям
`bronze/appstore_rss/snapshot_date=D/<country>_<feed>.json` и `bronze/appstore_itunes/…`. Формат записи тот
же, отличается только `_source` (`ingestion-apple-rss`). Перенос делает
[`scripts/migrate_azure_bronze.sh`](../scripts/migrate_azure_bronze.sh) (Storage Transfer Service, пути
`appstore_rss/` → `apple_rss/top_charts/`, `appstore_itunes/` → `apple_itunes/lookup/`), затем silver
пересобирается запуском `{"rebuild_silver": true}`. Пошагово — в [owner-tasks.md](owner-tasks.md).
