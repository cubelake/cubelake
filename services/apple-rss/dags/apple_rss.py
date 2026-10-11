"""apple-rss: daily top charts → bronze → silver_top_apps. Runs the service image via Docker."""

import json
import os
from datetime import datetime, timedelta

from airflow.providers.docker.operators.docker import DockerOperator
from airflow.sdk import Asset, dag, task
from airflow.sdk.exceptions import AirflowSkipException
from docker.types import Mount

PREFIX = "APPLE_RSS_"
IMAGE = os.environ.get(f"{PREFIX}IMAGE", "apple-rss:local")
LAKE_VOLUME = os.environ.get(f"{PREFIX}LAKE_VOLUME")  # local dev only: named volume mounted at /lake

# Published for downstream services (apple-itunes, appstore-analytics).
SILVER = Asset(name="apple_rss_silver")

DOCKER = dict(
    image=IMAGE,
    docker_url=os.environ.get("DOCKER_HOST", "unix://var/run/docker.sock"),
    # service config only; never rendered in the UI
    private_environment={
        k: v for k, v in os.environ.items()
        if k.startswith(PREFIX) and k not in {f"{PREFIX}IMAGE", f"{PREFIX}LAKE_VOLUME"}
    },
    mounts=[Mount(source=LAKE_VOLUME, target="/lake", type="volume")] if LAKE_VOLUME else [],
    mount_tmp_dir=False,
    auto_remove="success",
)


@task
def dates_from(output: str) -> list[str]:
    dates = json.loads(output)
    if not dates:
        raise AirflowSkipException("Nothing to process")
    return dates


@dag(
    dag_id="apple_rss",
    schedule="@daily",
    start_date=datetime(2026, 4, 20),
    catchup=False,
    max_active_runs=1,
    default_args={"owner": "apple-rss", "retries": 1, "retry_delay": timedelta(minutes=1)},
    tags=["apple-rss", "elt"],
)
def apple_rss():
    extract = DockerOperator(task_id="extract", command=["extract", "--date", "{{ ds }}"], **DOCKER)
    pending = DockerOperator(task_id="pending", command=["pending"], do_xcom_push=True, **DOCKER)
    transform = DockerOperator.partial(
        task_id="transform", max_active_tis_per_dagrun=4, **DOCKER
    ).expand(command=dates_from(pending.output).map(lambda d: ["transform", "--date", d]))

    @task(outlets=[SILVER])
    def publish_silver() -> None:
        pass

    extract >> pending
    transform >> publish_silver()


apple_rss()
