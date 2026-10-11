"""appstore-analytics: join apple-rss + apple-itunes silver, then build the gold marts."""

import json
import os
from datetime import datetime, timedelta

from airflow.providers.docker.operators.docker import DockerOperator
from airflow.sdk import Asset, dag, task
from airflow.sdk.exceptions import AirflowSkipException
from docker.types import Mount

PREFIX = "APPSTORE_ANALYTICS_"
IMAGE = os.environ.get(f"{PREFIX}IMAGE", "appstore-analytics:local")
LAKE_VOLUME = os.environ.get(f"{PREFIX}LAKE_VOLUME")  # local dev only: named volume mounted at /lake

RSS_SILVER = Asset(name="apple_rss_silver")        # input, published by apple-rss
ITUNES_SILVER = Asset(name="apple_itunes_silver")  # input, published by apple-itunes
GOLD = Asset(name="appstore_gold")

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
DEFAULT_ARGS = {"owner": "appstore-analytics", "retries": 2, "retry_delay": timedelta(minutes=2)}


@task
def dates_from(output: str) -> list[str]:
    dates = json.loads(output)
    if not dates:
        raise AirflowSkipException("Nothing to process")
    return dates


@dag(
    dag_id="appstore_analytics",
    schedule=[RSS_SILVER, ITUNES_SILVER],
    start_date=datetime(2026, 4, 20),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["appstore-analytics", "silver", "gold"],
)
def appstore_analytics():
    pending_silver = DockerOperator(
        task_id="pending_silver", command=["pending", "--stage", "silver"], do_xcom_push=True, **DOCKER
    )
    silver = DockerOperator.partial(
        task_id="silver", max_active_tis_per_dagrun=4, **DOCKER
    ).expand(command=dates_from.override(task_id="silver_dates")(pending_silver.output).map(
        lambda d: ["silver", "--date", d]
    ))

    pending_gold = DockerOperator(
        task_id="pending_gold", command=["pending", "--stage", "gold"],
        do_xcom_push=True, trigger_rule="none_failed", **DOCKER,
    )
    gold_daily = DockerOperator.partial(
        task_id="gold_daily", max_active_tis_per_dagrun=4, **DOCKER
    ).expand(command=dates_from.override(task_id="gold_dates")(pending_gold.output).map(
        lambda d: ["gold-daily", "--date", d]
    ))
    dim_apps = DockerOperator(task_id="dim_apps", command=["dim-apps"], **DOCKER)

    @task(outlets=[GOLD])
    def publish_gold() -> None:
        pass

    silver >> pending_gold
    gold_daily >> dim_apps >> publish_gold()


@dag(
    dag_id="appstore_rank_history",
    schedule="0 4 1,15 * *",  # full recompute on the 1st and 15th
    start_date=datetime(2026, 4, 20),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["appstore-analytics", "gold", "history"],
)
def appstore_rank_history():
    DockerOperator(task_id="rank_history", command=["rank-history"], **DOCKER)


appstore_analytics()
appstore_rank_history()
