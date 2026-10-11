# Эксплуатация

## Локально (без облака)

Нужны [uv](https://docs.astral.sh/uv/), [just](https://github.com/casey/just), Node 20+, Terraform 1.9+ и Docker.

```bash
just check                                   # всё, что проверяет CI
just test                                    # pytest + import-linter
just dataform-compile 2026-10-11             # компиляция SQLX за выбранный день
just tf-validate                             # terraform fmt + validate
just ingest apple-rss 2026-10-11 /tmp/lake   # настоящий запрос к Apple в локальную папку
just image                                   # Docker-образ для локальной проверки
```

`apple-itunes` локально не запустится: ему нужна таблица `silver_apple_rss.top_apps` в BigQuery.

Конфигурация ingest задаётся только переменными окружения:

| Переменная | Пример |
| --- | --- |
| `APPLE_RSS_BRONZE_URI` | `gs://cbl-d-bronze-7f3c/apple_rss/top_charts` или локальный путь |
| `APPLE_ITUNES_BRONZE_URI` | `gs://cbl-d-bronze-7f3c/apple_itunes/lookup` |
| `APPLE_ITUNES_TOP_APPS_TABLE` | `prj-d-cubelake-a1b2.silver_apple_rss.top_apps` |

В облаке эти переменные задаёт Terraform (`infra/terraform/ingest.tf`), `.env`-файлы не нужны.

## Выкладка

Первичная настройка описана пошагово в [owner-tasks.md](owner-tasks.md). Дальнейшие изменения:

| Что поменяли | Что сделать |
| --- | --- |
| SQLX (`definitions/`) | смержить в `main`; Dataform сам берёт `main` при следующем запуске |
| Python (`src/`) | собрать образ `linux/amd64`, запушить с тегом = git SHA, затем `terraform apply -var ingest_image_tag=<sha>` |
| `workflows/*.yaml` или `infra/terraform/` | `terraform apply` |

Пока CD не настроен, всё это делается руками. Потом это будет делать GitHub Actions через WIF.

```bash
SHA=$(git rev-parse --short HEAD)
IMAGE=$(terraform -chdir=infra/terraform output -raw ingest_image)
docker build --platform linux/amd64 -t "$IMAGE:$SHA" . && docker push "$IMAGE:$SHA"
terraform -chdir=infra/terraform apply -var ingest_image_tag="$SHA"
```

> На Mac с Apple Silicon `--platform linux/amd64` **обязателен**, иначе Cloud Run не запустит образ.

## Запуск руками

```bash
# весь пайплайн за сегодня (UTC)
gcloud workflows run cubelake-daily --location europe-central2

# за конкретный день (перезапуск или догрузка)
gcloud workflows run cubelake-daily --location europe-central2 --data='{"snapshot_date":"2026-10-11"}'

# только один ingest
gcloud run jobs execute cubelake-ingest --region europe-central2 --args=apple-rss,--date,2026-10-11 --wait
```

Перезапуск безопасен: bronze перезаписывает файлы своего дня, а silver делает MERGE по ключу.

**Загрузка истории за много дней.** Запускайте workflow с `snapshot_date` по одному дню, в цикле. Apple не
отдаёт прошлые чарты, поэтому за прошлые дни сработает только Dataform по уже лежащему bronze, например
после переноса из Azure. Для этого есть два варианта:
- в консоли Dataform выполнить тег с `vars.snapshot_date` нужного дня;
- оставить `snapshot_date` пустым: тогда Dataform перечитает все дни сразу. Включите
  «full refresh», если меняли схему.

## Где смотреть, что случилось

| Что | Где |
| --- | --- |
| Запуски пайплайна | Console → Workflows → `cubelake-daily` → Executions |
| Логи ingest | Console → Cloud Run → Jobs → `cubelake-ingest` → Logs (строки `Batch i/N: ok=…, failed=…`, `Wrote X/Y`) |
| Запуски Dataform и ошибки SQL | Console → Dataform → `cubelake` → Workflow execution logs |
| Упавшая проверка качества | запрос к view из `dataform_assertions`: он возвращает плохие строки |
| Файлы bronze | `gcloud storage ls gs://<bronze>/apple_rss/top_charts/snapshot_date=2026-10-11/` |

### Частые ошибки

| Симптом | Причина / что делать |
| --- | --- |
| `apple-rss` пишет `Wrote 200/350` | Apple RSS часто отвечает `ReadTimeout` и `502`. Записывается то, что удалось скачать, а остальное за этот день потеряно. Если не получилось ничего, job падает. Перезапустите день. |
| `apple-itunes`: `No charted apps …` | silver за этот день пуст: шаг `apple_rss_silver` не прошёл или bronze пуст |
| Dataform: `Cannot query … without a filter over column snapshot_date` | в модели нет `${snapshot.filter(...)}` по bronze-таблице |
| Новые bronze-файлы не видны в BigQuery | кэш метаданных BigLake обновляется до 4 часов; можно выполнить `CALL BQ.REFRESH_EXTERNAL_METADATA_CACHE('<project>.bronze_apple_rss.top_charts')` |
| Cloud Run: `exec format error` | образ собран под arm64; соберите заново с `--platform linux/amd64` |

## Новый источник

Пример: источник `google_play`.

1. **Ingest:**
   - создать `src/cubelake_ingest/google_play/` с файлами `config.py` (env `GOOGLE_PLAY_*`) и
     `ingest.py` (`ingest(settings, snapshot_date)`); писать через `core.bronze` и `core.storage`;
   - добавить ветку в `cli.py`;
   - дописать модуль в контракт `independence` в `pyproject.toml`;
   - добавить тесты в `tests/google_play/`.
2. **Bronze:**
   - схема `infra/terraform/schemas/bronze_google_play_<dataset>.json`;
   - датасеты `bronze_google_play` и `silver_google_play` и запись в `bronze_tables` в `bigquery.tf`;
   - env-переменная в `ingest.tf`;
   - права `sa-dataform` в `dataform.tf`.
3. **Silver:**
   - `definitions/sources/google_play/google_play.js` (declare);
   - `definitions/sources/google_play/google_play_<table>.sqlx` с `tags: ["google_play"]`.
4. **Оркестрация:** шаги `google_play_bronze` и `google_play_silver` в `workflows/cubelake-daily.yaml`.
5. Проверка: `just check`.

## Затраты (ориентир)

При текущем объёме (несколько сотен файлов по ~100 КБ в день) всё укладывается в бесплатные лимиты или в
копейки:
- Cloud Run job: несколько минут в день;
- BigQuery on-demand: запросы с фильтром по партиции;
- Workflows: десятки шагов в день;
- GCS: гигабайты.

Всё равно поставьте бюджет с оповещением, см. [owner-tasks.md](owner-tasks.md).
