# infra

> Docker Compose stack, Dockerfiles, and CI for the [Cubelake](https://github.com/Cubelake/cubelake) data platform.

![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Airflow](https://img.shields.io/badge/Apache_Airflow-3.2-017CEE?logo=apacheairflow&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

Every Dockerfile and Compose file here is designed to be built from the **`cubelake` monorepo root**, not from inside this submodule — they expect sibling directories (`appstore-core`, `appstore-dags`, `appstore-transform`, `ingestion-apple-rss`, `ingestion-apple-itunes`) and the workspace's root `pyproject.toml`/`uv.lock` to exist two levels up.

---

## Layout

```
infra/
├── appstore-dags/
│   ├── docker-compose.yml   # full Airflow stack
│   └── dockerfile           # apache/airflow:3.2.0-python3.13 + workspace deps
├── ingestion-apple-itunes/
│   └── dockerfile           # python:3.13-slim + workspace deps
└── ingestion-apple-rss/
    └── dockerfile           # python:3.13-slim + workspace deps
```

## Airflow stack (`appstore-dags/docker-compose.yml`)

```bash
cd infra/appstore-dags
docker compose up airflow-init   # first time only: DB migration + admin user
docker compose up -d             # start everything
docker compose --profile debug run airflow-cli airflow dags list  # optional CLI shell
```

| Service | Role |
|---|---|
| `postgres` | Airflow metadata DB (`postgres:16`) |
| `airflow-apiserver` | Airflow 3.x API server (replaces the classic webserver) — UI at `:8080` |
| `airflow-scheduler` | Task scheduling |
| `airflow-dag-processor` | Parses DAG files (split out from the scheduler in Airflow 3.x) |
| `airflow-triggerer` | Deferred/async task triggers |
| `airflow-init` | One-shot: resource checks, DB migration, admin user creation |
| `airflow-cli` | Opt-in (`--profile debug`) shell for `airflow` CLI commands |

Key mounts: `appstore-dags/{dags,logs,config,plugins}` and `appstore-transform` (bind-mounted read-write to `/opt/airflow/dbt/appstore-transform`) — both DAG code and dbt models are picked up live without rebuilding the image. `appstore-dags` itself is **not** installed as a Python package inside the container; only its dependencies (`appstore-core`, `ingestion-apple-rss`, `ingestion-apple-itunes`, plus `apache-airflow`/`duckdb`/`dbt-duckdb`) are baked in during the image build.

## Dockerfiles

All three follow the same pattern: install [`uv`](https://github.com/astral-sh/uv), copy in the root `pyproject.toml`/`uv.lock` plus the relevant workspace packages, run `uv export --package <name> --no-dev -o requirements.txt` (stripping local `-e` entries), `pip install` the result, then `pip install --no-deps` the local workspace packages on top. None define an `ENTRYPOINT`/`CMD` for the two ingestion-service images — they're built for `docker run <image> python -m ...`-style invocation or as a base for a future scheduler/job runner, not run directly by anything in this repo yet.

```bash
# example: build the DAGs image from the monorepo root
docker build -f infra/appstore-dags/dockerfile -t cubelake/appstore-dags .
```

## Environment variables

There's no `.env.example` yet — create `infra/appstore-dags/.env` with:

```bash
AIRFLOW_UID=50000                 # set to `id -u` on Linux hosts
POSTGRES_USER=airflow
POSTGRES_PASSWORD=airflow

ACCOUNT_URL=https://<storage_account>.dfs.core.windows.net
BRONZE_RSS_SAS_TOKEN=...
SILVER_RSS_SAS_TOKEN=...
BRONZE_ITUNES_SAS_TOKEN=...
SILVER_ITUNES_SAS_TOKEN=...
SILVER_APPSTORE_SAS_TOKEN=...
GOLD_SAS_TOKEN=...
```

This file is gitignored everywhere in this repo (`.env`, `.dockerignore`) — it never enters git history or the Docker build context.

## CI

`.github/workflows/update-parent.yml` runs on every push to `main`: it checks out the parent `cubelake` repo, fast-forwards the `infra` submodule pointer to this commit, and pushes the result. There is no lint/test/build-and-push-image workflow in this repo yet.

## Known limitations

- No `.env.example` template.
- No compose service or CI job actually runs the two ingestion-service images — they're built but not yet wired into an orchestrator here.
- `AIRFLOW__CORE__FERNET_KEY` defaults to an empty string in the compose file — fine for local dev, must be set to a real key for anything shared.

## License

[MIT](LICENSE)
