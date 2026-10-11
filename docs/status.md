# Статус: где остановились (2026-10-11)

Проект **на паузе**: код облачной части готов и проверен офлайн, но GCP не развёрнут, потому что у
аккаунта нет billing account. Этот документ — точка входа, чтобы продолжить с того же места.

## Готово

- Код: ingest (Python, `src/cubelake_ingest/`), Dataform (`definitions/`), Workflows
  (`workflows/cubelake-daily.yaml`), Terraform (`infra/terraform/`), скрипт переноса из Azure
  (`scripts/migrate_azure_bronze.sh`). Слои: bronze и silver.
- Локальные проверки зелёные (`just check`): 13 тестов, границы модулей, компиляция Dataform,
  `terraform validate`, сборка Docker-образа. Реальная выгрузка Apple RSS в локальную папку работает.
- CI на `main` зелёный: `python`, `dataform`, `terraform`, `secrets` (бесплатный gitleaks CLI).
- Документация: [architecture](architecture.md), [data-flow](data-flow.md), [data](data.md),
  [operations](operations.md), [owner-tasks](owner-tasks.md).
- Google Cloud:
  - аккаунт `mykhailolaskavyi@gmail.com`, `gcloud auth login` выполнен;
  - рабочая организация — **`230879006059`** (из трёх одноимённых `mykhailolaskavyi-org`);
  - все старые проекты удалены 2026-10-11, окончательно сотрутся около 2026-11-10.

## Что блокирует

**Billing account.** Без него в GCP не работает ничего из нашего стека, даже бесплатный уровень
(Cloud Run, Workflows, Scheduler, Dataform, GCS, Storage Transfer). Создание:
https://console.cloud.google.com/billing/create?organizationId=230879006059. Банк временно блокирует
около NOK 540 на карте (снимается в течение недели).

## Как продолжить

1. Billing account + бюджет $10/мес — [owner-tasks.md §3](owner-tasks.md#3-аккаунт-и-проект-google-cloud).
2. Dev-проект `prj-d-cubelake-<rand>` в организации `230879006059`, state-бакет, GitHub-токен для Dataform —
   §3–4.
3. Первый деплой в три шага (реестр образов → образ `linux/amd64` → полный `terraform apply`) — §5.
4. Первый прогон workflow и проверки — §6.
5. Перенос bronze из Azure скриптом и `{"rebuild_silver": true}` — §7.

## Риски первого запуска (ни разу не выполнялось в облаке)

- SQL silver-моделей в диалекте BigQuery (переписан с DuckDB вручную). Можно проверить заранее и
  бесплатно в BigQuery sandbox (без billing): загрузить bronze-файлы `bq load` и выполнить SELECT моделей.
- Создание Iceberg-таблиц Dataform-ом и `ALTER PROJECT … default_cloud_resource_connection_id`.
- Синтаксис Workflows, достаточность IAM, фильтр `snapshot_date IS NOT NULL` для `require_partition_filter`
  в режиме `rebuild_silver`.
- Перенос из Azure через Storage Transfer.

## Отложенные идеи

- **~20 источников.** Реестр источников в Terraform (`for_each`), по Cloud Run job и сервисному аккаунту
  на источник (общий образ), общий workflow с параллельными волнами по зависимостям, Scheduler на каждую
  периодичность, алерты на падения. Где возможно — управляемые коннекторы Google (BigQuery Data Transfer
  для SaaS, Datastream для БД, Storage Transfer для файлов). Composer (Airflow) — только если появится много
  перекрёстных зависимостей между источниками.
- CD из GitHub Actions через Workload Identity Federation.
- Prod-проект `prj-p-cubelake-<rand>`.
- Gold-слой и джойн источников (`definitions/intermediate/`, `definitions/outputs/`).

## Параллельная Azure-версия

Пока GCP на паузе, рабочая версия пайплайна живёт в Azure как отдельный проект (bronze + silver).
Формат bronze у них общий (`_source`, `_ingested_at`, `_feed_type`, `country` + ответ API,
`snapshot_date=YYYY-MM-DD/<country>_<feed>.json`), поэтому накопленные в Azure данные переносятся сюда
скриптом без изменений.
