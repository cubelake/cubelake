import json
import os
import subprocess

from airflow.sdk import Asset, dag, task
from airflow.sdk.exceptions import AirflowSkipException
from azure.storage.filedatalake import DataLakeServiceClient
from common.storage.azure_tokens import AppstoreSilverToken, GoldToken
from common.storage.containers import ADLS_GOLD_CONTAINER, ADLS_SILVER_CONTAINER

from dags.silver.appstore.transform_appstore_apps_daily import SILVER_APPSTORE_APPS
from dags.utils.default_args import gold_args

DBT_PROJECT_DIR = os.environ.get("DBT_PROJECT_DIR", "/opt/airflow/dbt/appstore-transform")

GOLD_APPSTORE_DAILY = Asset("azure://gold/appstore_daily")


@dag(
    dag_id="gold_transform_daily",
    default_args=gold_args,
    schedule=[SILVER_APPSTORE_APPS],
    max_active_runs=1,
    catchup=False,
    tags=["gold", "apps", "transform", "daily"],
)
def gold_transform_daily():
    @task(task_id="discover_missing_snapshots")
    def discover_missing_snapshots() -> list[str]:
        appstore_silver = AppstoreSilverToken()
        gold = GoldToken()

        def _snapshot_dates(client: DataLakeServiceClient, container: str, prefix: str) -> set[str]:
            fs = client.get_file_system_client(container)
            try:
                return {
                    p.name.split("snapshot_date=")[-1]
                    for p in fs.get_paths(prefix, recursive=False)
                    if p.is_directory and "snapshot_date=" in p.name
                }
            except Exception:
                return set()

        silver_client = DataLakeServiceClient(
            account_url=appstore_silver.account_url, credential=appstore_silver.sas_token
        )
        gold_client = DataLakeServiceClient(
            account_url=gold.account_url, credential=gold.sas_token
        )

        silver_dates = _snapshot_dates(silver_client, ADLS_SILVER_CONTAINER, "appstore")
        gold_dates = _snapshot_dates(gold_client, ADLS_GOLD_CONTAINER, "fct_top_apps")

        missing = sorted(silver_dates - gold_dates)
        if not missing:
            raise AirflowSkipException("All silver snapshots already in gold fct_top_apps")

        return missing

    @task(task_id="run_dbt_transform", max_active_tis_per_dagrun=4)
    def run_dbt_transform(snapshot_date: str) -> None:
        appstore_silver = AppstoreSilverToken()
        gold = GoldToken()
        account_name = appstore_silver.account_url.split("://")[1].split(".")[0]

        env = {
            **os.environ,
            "ACCOUNT_NAME": account_name,
            "SILVER_SAS_TOKEN": appstore_silver.sas_token,
            "GOLD_SAS_TOKEN": gold.sas_token,
        }
        result = subprocess.run(
            [
                "dbt", "run",
                "--select", "gold_fct_top_apps gold_fct_genre_stats",
                "--vars", json.dumps({"snapshot_date": snapshot_date}),
                "--project-dir", DBT_PROJECT_DIR,
                "--profiles-dir", DBT_PROJECT_DIR,
                "--target-path", f"/tmp/dbt_target_gold_{snapshot_date}",
            ],
            env=env,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"dbt gold run failed for {snapshot_date}:\n{result.stdout}\n{result.stderr}")

    @task(task_id="emit_gold_appstore_daily_asset", outlets=[GOLD_APPSTORE_DAILY])
    def emit_gold_appstore_daily_asset(results: list) -> None:
        pass

    missing_dates = discover_missing_snapshots()
    dbt_done = run_dbt_transform.expand(snapshot_date=missing_dates)
    emit_gold_appstore_daily_asset(dbt_done)


gold_transform_daily()
