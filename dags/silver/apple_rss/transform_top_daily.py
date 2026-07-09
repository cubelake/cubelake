import json
import os
import subprocess

from airflow.sdk import Asset, dag, task
from airflow.sdk.exceptions import AirflowSkipException
from apple_rss.storage import RssBronzeToken, RssSilverToken
from apple_rss.storage.containers import ADLS_BRONZE_CONTAINER, ADLS_SILVER_CONTAINER
from azure.core.exceptions import ResourceNotFoundError
from azure.storage.filedatalake import DataLakeServiceClient

from dags.bronze.apple_rss.apple_top_daily import BRONZE_APPSTORE_RSS
from dags.utils.default_args import silver_args

DBT_PROJECT_DIR = os.environ.get("DBT_PROJECT_DIR", "/opt/airflow/dbt/appstore-transform")

SILVER_APPSTORE_RSS = Asset("azure://silver/appstore_rss")


@dag(
    dag_id="silver_transform_top_daily",
    default_args=silver_args,
    schedule=[BRONZE_APPSTORE_RSS],
    max_active_runs=1,
    catchup=False,
    tags=["silver", "apps", "transform", "normalize", "daily"],
)
def silver_transform_top_daily():
    @task(task_id="discover_bronze_snapshots")
    def discover_bronze_snapshots() -> list[str]:
        bronze = RssBronzeToken()
        silver = RssSilverToken()

        def _snapshot_dates(client: DataLakeServiceClient, container: str) -> set[str]:
            fs = client.get_file_system_client(container)
            try:
                return {
                    p.name.split("snapshot_date=")[-1]
                    for p in fs.get_paths("appstore_rss", recursive=False)
                    if p.is_directory and "snapshot_date=" in p.name
                }
            except ResourceNotFoundError:
                return set()

        bronze_dates = _snapshot_dates(
            DataLakeServiceClient(account_url=bronze.account_url, credential=bronze.sas_token),
            ADLS_BRONZE_CONTAINER,
        )
        silver_dates = _snapshot_dates(
            DataLakeServiceClient(account_url=silver.account_url, credential=silver.sas_token),
            ADLS_SILVER_CONTAINER,
        )

        missing = sorted(bronze_dates - silver_dates)

        if not missing:
            raise AirflowSkipException("All bronze snapshots already processed into silver")

        return missing

    @task(task_id="run_dbt_transform", max_active_tis_per_dagrun=4)
    def run_dbt_transform(snapshot_date: str) -> None:
        bronze = RssBronzeToken()
        silver = RssSilverToken()
        account_name = bronze.account_url.split("://")[1].split(".")[0]

        env = {
            **os.environ,
            "ACCOUNT_NAME": account_name,
            "BRONZE_SAS_TOKEN": bronze.sas_token,
            "SILVER_SAS_TOKEN": silver.sas_token,
        }
        result = subprocess.run(
            [
                "dbt", "run",
                "--select", "+silver_top_apps",
                "--vars", json.dumps({"snapshot_date": snapshot_date}),
                "--project-dir", DBT_PROJECT_DIR,
                "--profiles-dir", DBT_PROJECT_DIR,
                "--target-path", f"/tmp/dbt_target_{snapshot_date}",
            ],
            env=env,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"dbt run failed for {snapshot_date}:\n{result.stdout}\n{result.stderr}")

    @task(task_id="emit_silver_rss_asset", outlets=[SILVER_APPSTORE_RSS])
    def emit_silver_rss_asset(results: list) -> None:
        pass

    missing_dates = discover_bronze_snapshots()
    dbt_done = run_dbt_transform.expand(snapshot_date=missing_dates)
    emit_silver_rss_asset(dbt_done)


silver_transform_top_daily()
