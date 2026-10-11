# Архитектура

Cubelake собирает данные Apple App Store и раскладывает их по схеме
[Google Cloud Lakehouse](https://docs.cloud.google.com/lakehouse/docs/key-concepts) (medallion).
Сейчас в работе два слоя — **bronze** и **silver**. Gold (джойны, витрины) появится позже.

## ELT: кто за что отвечает

| Шаг | Что делает | Чем сделан | Где код |
| --- | --- | --- | --- |
| **E + L** (ingest) | Забирает ответы API и кладёт их как есть в bronze-бакет | Python, Cloud Run job `cubelake-ingest` | `src/cubelake_ingest/` |
| **T** (transform) | Превращает bronze в типизированные таблицы silver и проверяет качество | Dataform (SQLX) | `definitions/`, `includes/` |
| Оркестрация | Каждый день по порядку запускает ingest → Dataform для каждого источника | Cloud Scheduler + Cloud Workflows | `workflows/cubelake-daily.yaml` |
| Инфраструктура | Всё перечисленное выше плюс бакеты, датасеты, IAM | Terraform | `infra/terraform/` |

Почему именно эти технологии: так рекомендует документация Google для serverless-lakehouse. Здесь нет
VM, Airflow, dbt и DuckDB — нечего патчить и не за что платить, пока ничего не запущено.

## Слои

| Слой | Значение у Google | У нас | Хранение |
| --- | --- | --- | --- |
| bronze | raw: данные как пришли | ответы Apple RSS / iTunes lookup | NDJSON в GCS → BigLake external tables в BigQuery |
| silver | cleansed: очищено, типизировано | одна строка на сущность в день | Apache Iceberg managed tables в BigQuery (файлы в нашем бакете) |
| gold | curated: бизнес-витрины | **пока нет** | — |

Как устроены данные в каждом слое, описано в [data.md](data.md).

## Ежедневный поток

```text
Cloud Scheduler  "17 6 * * *" UTC
  └─ Workflows cubelake-daily (snapshot_date = сегодня по UTC или аргумент)
       1. apple_rss_bronze     Cloud Run job: cubelake-ingest apple-rss --date D
                               → gs://cbl-<env>-bronze-<rand>/apple_rss/top_charts/snapshot_date=D/*.json
       2. apple_rss_silver     Dataform: compile(main, vars) → run tag "apple_rss"
                               → silver_apple_rss.top_apps (+ assertions)
       3. apple_itunes_bronze  Cloud Run job: cubelake-ingest apple-itunes --date D
                               (app_id берёт из silver_apple_rss.top_apps за день D)
                               → gs://…/apple_itunes/lookup/snapshot_date=D/*.json
       4. apple_itunes_silver  Dataform: run tag "apple_itunes"
                               → silver_apple_itunes.app_details (+ assertions)
```

Шаги идут строго по очереди: iTunes нужен готовый silver от RSS. Если шаг падает, весь workflow
останавливается с ошибкой, и следующие шаги не запускаются.

## Компоненты

### Ingest (Python)

- Один пакет `cubelake_ingest`, один образ и один Cloud Run job. Источник выбирается аргументом:
  `cubelake-ingest <apple-rss|apple-itunes> --date YYYY-MM-DD`.
- `core/` — общий код:
  - `http.py` — асинхронный GET пачками по 10 с паузой 4 с, таймаут 15 с, 2 повтора;
  - `bronze.py` — формат записи;
  - `storage.py` — запись через fsspec: `gs://…` в облаке, локальный путь в тестах.
- `apple_rss/`, `apple_itunes/` — по модулю на источник, у каждого свой `config.py` (env `APPLE_RSS_*`,
  `APPLE_ITUNES_*`). Источники **не импортируют друг друга**, а `core` не импортирует источники.
  Это проверяет `import-linter` в CI.
- Новый источник — новая папка рядом. Шаги описаны в [operations.md](operations.md#новый-источник).

### Transform (Dataform)

- Проект лежит в **корне репозитория** (`workflow_settings.yaml`), потому что managed Dataform не умеет
  читать проект из подпапки.
- Раскладка по [рекомендациям Google](https://docs.cloud.google.com/dataform/docs/best-practices-repositories):
  - `definitions/sources/<source>/<source>.js` — объявление bronze-таблицы;
  - `definitions/sources/<source>/<source>_<table>.sqlx` — silver-модель (`name:` задаёт имя таблицы);
  - позже `definitions/intermediate/` (джойны) и `definitions/outputs/<entity>/` (gold).
- Silver-модели устроены так:
  - `type: "incremental"` с `uniqueKey`, то есть MERGE: повторный прогон дня ничего не дублирует;
  - Iceberg (`iceberg: { bucketName, tableFolderRoot: "iceberg" }`);
  - партиция по `snapshot_date`, кластеризация по `country, feed_type`.
- Переменные (`vars`) workflow передаёт при компиляции:
  - `snapshot_date` — какой день обрабатывать; пусто = все дни;
  - `silver_bucket`.
- Проверки качества записаны в `assertions` прямо в модели: not null, уникальность ключа, допустимые
  значения. Если проверка падает, падает весь workflow.

### Оркестрация (Workflows + Scheduler)

- `workflows/cubelake-daily.yaml` — основной сценарий и две подпрограммы:
  - `ingest` запускает Cloud Run job и ждёт окончания;
  - `dataform` компилирует ветку `main`, запускает нужный тег и опрашивает статус каждые 20 с.
- Terraform прокидывает в workflow переменные окружения `REGION`, `INGEST_JOB`, `DATAFORM_REPOSITORY`,
  `SILVER_BUCKET`.
- Scheduler вызывает workflow с пустым аргументом, и тогда дата берётся по UTC.

### Инфраструктура (Terraform, `infra/terraform/`)

| Файл | Что создаёт |
| --- | --- |
| `versions.tf` | провайдеры google и google-beta (Dataform есть только в beta), state в GCS |
| `main.tf` | включение API, случайный суффикс имён |
| `storage.tf` | бакеты bronze (с версионированием, Nearline после 90 дней) и silver |
| `bigquery.tf` | датасеты, BigLake connection `lake`, connection по умолчанию для Iceberg, bronze external tables (схемы в `schemas/*.json`) |
| `ingest.tf` | Artifact Registry `cubelake`, `sa-ingest`, Cloud Run job |
| `dataform.tf` | Dataform repository (берёт код из GitHub, токен в Secret Manager), сервисный агент Dataform, `sa-dataform` |
| `orchestration.tf` | `sa-workflows`, workflow, Scheduler |

## Безопасность

- **Ключей сервисных аккаунтов нет.** Всё в облаке работает от своих SA. CD из GitHub будет работать через
  Workload Identity Federation, тоже без ключей.
- **Минимальные права:**

  | Сервисный аккаунт | Может |
  | --- | --- |
  | `sa-ingest` | писать объекты в bronze-бакет, читать `silver_apple_rss`, запускать запросы BigQuery |
  | `sa-dataform` | читать bronze-датасеты, писать silver и `dataform_assertions`, создавать Iceberg через connection `lake` |
  | SA connection `lake` | читать bronze-бакет, писать silver-бакет (реальный файловый I/O BigQuery) |
  | `sa-workflows` | запускать только job `cubelake-ingest`, работать с Dataform, писать логи |

- Бакеты: uniform bucket-level access, публичный доступ запрещён (`public_access_prevention = enforced`).
- Имена бакетов не содержат имени проекта и заканчиваются случайным суффиксом, чтобы их было трудно угадать.
- Секреты хранятся только в Secret Manager (GitHub-токен для Dataform). В репозитории секретов нет, это
  проверяет `gitleaks` в CI. В `.gitleaksignore` записаны три старых локальных ключа Airflow из истории
  git; они нигде не используются.
- Образ запускается от непривилегированного пользователя (uid 10001), в образ попадают только
  `pyproject.toml`, `uv.lock` и `src/`.

## CI (`.github/workflows/ci.yml`)

Запускается на каждый PR и push в `main`. Облако для этого не нужно.

| Job | Проверяет |
| --- | --- |
| `python` | `uv sync --locked`, pytest, import-linter, сборку Docker-образа |
| `dataform` | компиляцию SQLX; падает на ошибках компиляции |
| `terraform` | `fmt -check`, `validate` |
| `secrets` | gitleaks CLI по всей истории git (не `gitleaks-action`: ему нужна платная лицензия для организаций) |

CD (сборка и выкладка образа, `terraform apply`) появится после создания GCP-проекта.

## Что проверено, а что нет

Проверено офлайн: тесты, границы модулей, компиляция Dataform, `terraform validate`, сборка образа,
реальная выгрузка Apple RSS в локальную папку.

**Не проверено, пока нет GCP:**
- SQL в диалекте BigQuery (переписан вручную с DuckDB);
- создание Iceberg-таблиц Dataform-ом;
- `ALTER PROJECT … default_cloud_resource_connection_id`;
- синтаксис Workflows;
- достаточность IAM-прав.

Первый прогон в облаке почти наверняка найдёт несколько ошибок, их надо будет поправить.
