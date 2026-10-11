"""apple-itunes: look up apps charted by apple-rss → bronze → silver_itunes_app_details."""

import json
import os
from datetime import datetime, timedelta

from airflow.providers.docker.operators.docker import DockerOperator
from airflow.sdk import Asset, dag, task
from airflow.sdk.exceptions import AirflowSkipException
from docker.types import Mount

PREFIX = "APPLE_ITUNES_"
IMAGE = os.environ.get(f"{PREFIX}IMAGE", "apple-itunes:local")
LAKE_VOLUME = os.environ.get(f"{PREFIX}LAKE_VOLUME")  # local dev only: named volume mounted at /lake

RSS_SILVER = Asset(name="apple_rss_silver")  # input, published by apple-rss
SILVER = Asset(name="apple_itunes_silver")   # output, consumed by appstore-analytics

DOCKER = dict(
    image=IMAGE,
    docker_url=os.environ.get("DOCKER_HOST", "unix://var/run/docker.sock"),
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
    dag_id="apple_itunes",
    schedule=[RSS_SILVER],
    start_date=datetime(2026, 4, 20),
    catchup=False,
    max_active_runs=1,
    default_args={"owner": "apple-itunes", "retries": 1, "retry_delay": timedelta(minutes=1)},
    tags=["apple-itunes", "elt"],
)
def apple_itunes():
    pending_extract = DockerOperator(
        task_id="pending_extract", command=["pending", "--stage", "extract"], do_xcom_push=True, **DOCKER
    )
    # one day at a time: the iTunes API rate-limits aggressively
    extract = DockerOperator.partial(
        task_id="extract", max_active_tis_per_dagrun=1, **DOCKER
    ).expand(command=dates_from.override(task_id="extract_dates")(pending_extract.output).map(
        lambda d: ["extract", "--date", d]
    ))

    # runs even when nothing new was extracted, to pick up any untransformed backlog
    pending_transform = DockerOperator(
        task_id="pending_transform", command=["pending", "--stage", "transform"],
        do_xcom_push=True, trigger_rule="none_failed", **DOCKER,
    )
    transform = DockerOperator.partial(
        task_id="transform", max_active_tis_per_dagrun=4, **DOCKER
    ).expand(command=dates_from.override(task_id="transform_dates")(pending_transform.output).map(
        lambda d: ["transform", "--date", d]
    ))

    @task(outlets=[SILVER])
    def publish_silver() -> None:
        pass

    extract >> pending_transform
    transform >> publish_silver()


apple_itunes()
