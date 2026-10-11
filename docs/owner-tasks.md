# Что нужно сделать владельцу

Задачи идут по порядку. Блоки 0–1 можно сделать прямо сейчас, остальным нужен аккаунт Google Cloud.
Отмечайте `[x]` по мере выполнения. Если что-то пошло не так, пришлите текст ошибки.

## 0. Решения и безопасность (сейчас)

- [ ] **Слить ветку `lakehouse` в `main`.** Dataform в облаке компилирует только `main`, поэтому без
  слияния он ничего не увидит. Варианты: PR (CI прогонит проверки) или прямой merge. Скажите, какой вариант
  выбираете, и я сделаю push.
- [ ] **Отозвать `PARENT_REPO_TOKEN`.** Это старый GitHub-токен из прежней схемы с подмодулями.
  1. GitHub → аватар → Settings → Developer settings → Personal access tokens (fine-grained и classic).
  2. Найти токен, которым пользовался `PARENT_REPO_TOKEN`, и нажать **Revoke**.
  3. В бывших репозиториях: Settings → Secrets and variables → Actions → удалить `PARENT_REPO_TOKEN`
     (если там ещё есть).
- [ ] **Проверить, что репозитории приватные:** github.com/cubelake → Repositories, у каждого метка
  **Private**.

## 1. Уборка на ноутбуке (по желанию)

Старые папки после разделения на сервисы больше не нужны, весь код теперь в `cubelake`. В
`cubelake-platform/.env` лежат локальные ключи Airflow.

- [ ] Убедиться, что в этих папках нет незакоммиченного нужного (`git status` в каждой).
- [ ] Удалить:
  ```bash
  cd ~/Documents && rm -rf apple-rss apple-itunes appstore-analytics cubelake-contracts cubelake-platform
  ```
- [ ] Удалить старые Docker-тома и образы Airflow/DuckDB:
  ```bash
  docker volume ls            # посмотреть, что есть
  docker volume rm <имя> …    # удалить ненужные
  docker image prune -a       # удалить неиспользуемые образы
  ```

## 2. Инструменты

- [ ] Google Cloud CLI: `brew install --cask google-cloud-sdk`, затем `gcloud --version`.
- [ ] Остальное уже стоит, если `just check` проходит: uv, just, node, terraform, docker.

## 3. Аккаунт и проект Google Cloud

- [ ] Зарегистрироваться на https://console.cloud.google.com. Новым аккаунтам дают $300 кредитов на 90 дней.
- [ ] Создать **billing account** (Billing → Create account), привязать карту.
- [ ] **Бюджет с оповещением:** Billing → Budgets & alerts → Create budget, например $10 в месяц,
  уведомления на 50/90/100%. Это защитит от неожиданных счетов.
- [ ] Создать dev-проект. Имя по нашему правилу: `prj-d-cubelake-<4 случайных символа>`.
  ```bash
  gcloud auth login
  P=prj-d-cubelake-$(openssl rand -hex 2)      # запомните это значение
  gcloud projects create $P
  gcloud billing accounts list                 # возьмите ACCOUNT_ID
  gcloud billing projects link $P --billing-account=<ACCOUNT_ID>
  gcloud config set project $P
  gcloud auth application-default login        # даёт Terraform ваши права
  ```

## 4. Подготовка, которую Terraform не делает

- [ ] Включить API для подготовки:
  ```bash
  gcloud services enable storage.googleapis.com secretmanager.googleapis.com
  ```
- [ ] **Бакет для Terraform state** (один на проект):
  ```bash
  gcloud storage buckets create gs://$P-tfstate --location=europe-central2 \
    --uniform-bucket-level-access --public-access-prevention
  gcloud storage buckets update gs://$P-tfstate --versioning
  ```
- [ ] **GitHub-токен для Dataform.** Dataform берёт SQLX из GitHub и только читает.
  1. GitHub → Settings → Developer settings → Fine-grained tokens → Generate new token.
  2. Resource owner: `cubelake`. Repository access: Only select → `cubelake`.
     Permissions → Repository → **Contents: Read-only**. Срок — например 1 год (поставьте напоминание
     о продлении).
  3. Сохранить в Secret Manager (токен не попадает ни в историю shell, ни в репозиторий):
     ```bash
     read -s TOKEN && printf %s "$TOKEN" | gcloud secrets create dataform-github-token \
       --replication-policy=user-managed --locations=europe-central2 --data-file=- && unset TOKEN
     ```

## 5. Первый деплой

- [ ] Заполнить переменные:
  ```bash
  cd infra/terraform
  cp terraform.tfvars.example terraform.tfvars   # project_id = "<P>", env = "d"
  terraform init -backend-config="bucket=$P-tfstate"
  ```
- [ ] **Шаг 1 — API и реестр образов.** Сначала их, потому что Cloud Run job нельзя создать без
  существующего образа:
  ```bash
  terraform apply -target=google_project_service.apis -target=google_artifact_registry_repository.images
  ```
- [ ] **Шаг 2 — собрать и запушить образ** (из корня репозитория):
  ```bash
  gcloud auth configure-docker europe-central2-docker.pkg.dev
  SHA=$(git rev-parse --short HEAD)
  IMAGE=$(terraform -chdir=infra/terraform output -raw ingest_image 2>/dev/null \
          || echo europe-central2-docker.pkg.dev/$P/cubelake/cubelake-ingest)
  docker build --platform linux/amd64 -t "$IMAGE:$SHA" . && docker push "$IMAGE:$SHA"
  ```
- [ ] **Шаг 3 — всё остальное:**
  ```bash
  terraform -chdir=infra/terraform apply -var ingest_image_tag="$SHA"
  ```
  Если появится ошибка (IAM, BigQuery, Dataform), пришлите её текст. Это ожидаемо: облачная часть ещё
  ни разу не запускалась.

## 6. Первый прогон и проверка

- [ ] Запустить пайплайн и дождаться результата:
  ```bash
  gcloud workflows run cubelake-daily --location europe-central2
  ```
- [ ] Проверить, что всё на месте:
  ```bash
  B=$(terraform -chdir=infra/terraform output -raw bronze_bucket)
  gcloud storage ls gs://$B/apple_rss/top_charts/ | tail -1
  bq query --use_legacy_sql=false \
    'SELECT snapshot_date, COUNT(*) FROM silver_apple_rss.top_apps GROUP BY 1'
  bq query --use_legacy_sql=false \
    'SELECT snapshot_date, COUNT(*) FROM silver_apple_itunes.app_details GROUP BY 1'
  ```
- [ ] На следующий день убедиться, что Scheduler запустил workflow сам, в 06:17 UTC.

## 7. Перенос старого bronze из Azure

Делается скриптом [`scripts/migrate_azure_bronze.sh`](../scripts/migrate_azure_bronze.sh). Как он работает,
описано в [data-flow.md](data-flow.md#перенос-старых-данных-из-azure-однократно). Выполнять после шага 6,
когда bronze-бакет и таблицы уже существуют.

- [ ] Узнать имя storage account в Azure: Portal → Storage accounts. Container с сырыми данными называется
  `bronze`, внутри лежат папки `appstore_rss/` и `appstore_itunes/`.
- [ ] Создать SAS-токен: Portal → storage account → Containers → `bronze` → Shared access tokens →
  Permissions: **Read + List**, срок — неделя → Generate. Скопировать **Blob SAS token**. В чат его не
  присылайте, скрипт спросит токен сам и нигде его не сохранит.
- [ ] Проверить сопоставление путей (ничего не создаёт):
  ```bash
  AZURE_ACCOUNT=<имя> scripts/migrate_azure_bronze.sh --dry-run
  ```
- [ ] Запустить перенос и дождаться конца (скрипт покажет прогресс и количество перенесённых дней):
  ```bash
  AZURE_ACCOUNT=<имя> scripts/migrate_azure_bronze.sh
  ```
- [ ] Пересобрать silver за все дни:
  ```bash
  gcloud workflows run cubelake-daily --location europe-central2 --data='{"rebuild_silver": true}'
  ```
- [ ] Сверить: число дней в silver ≈ число дней в Azure.
  ```bash
  bq query --use_legacy_sql=false 'SELECT COUNT(DISTINCT snapshot_date) FROM silver_apple_rss.top_apps'
  ```
- [ ] Отозвать SAS-токен в Azure (или дождаться окончания срока).

## 8. Потом

- [ ] Prod-проект `prj-p-cubelake-<rand>`: те же шаги 3–6 с `env = "p"`.
- [ ] CD из GitHub Actions через Workload Identity Federation: сборка образа и `terraform apply` на merge
  в `main`. Сделаю я, от вас понадобится только подтверждение.
- [ ] После переноса из Azure: удалить данные в Azure и отключить там подписку.
- [ ] Gold-слой и джойн источников.
