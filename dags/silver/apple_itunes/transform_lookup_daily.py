import json
import os
import subprocess

from airflow.sdk import dag, task
from airflow.sdk.exceptions import AirflowSkipException
from apple_itunes.storage import ItunesBronzeToken, ItunesSilverToken
from azure.storage.filedatalake import DataLakeServiceClient
from common.storage.containers import ADLS_BRONZE_CONTAINER, ADLS_SILVER_CONTAINER

from dags.bronze.apple_itunes.apple_lookup_daily import BRONZE_APPSTORE_ITUNES
from dags.utils.default_args import silver_args

DBT_PROJECT_DIR = os.environ.get("DBT_PROJECT_DIR", "/opt/airflow/dbt/appstore-transform")


@dag(
    dag_id="silver_transform_itunes_lookup_daily",
    default_args=silver_args,
    schedule=[BRONZE_APPSTORE_ITUNES],
    max_active_runs=1,
    catchup=False,
    tags=["silver", "apps", "itunes", "transform", "normalize", "daily"],
)
def silver_transform_itunes_lookup_daily():
    @task(task_id="discover_bronze_snapshots")
    def discover_bronze_snapshots() -> list[str]:
        bronze = ItunesBronzeToken()
        silver = ItunesSilverToken()

        def _snapshot_dates(client: DataLakeServiceClient, container: str) -> set[str]:
            fs = client.get_file_system_client(container)
            return {
                p.name.split("snapshot_date=")[-1]
                for p in fs.get_paths("appstore_itunes", recursive=False)
                if p.is_directory and "snapshot_date=" in p.name
            }

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

    @task(task_id="run_dbt_transform")
    def run_dbt_transform(snapshot_date: str) -> None:
        bronze = ItunesBronzeToken()
        silver = ItunesSilverToken()
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
                "--select", "+silver_itunes_app_details",
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
            raise RuntimeError(
                f"dbt run failed for {snapshot_date}:\n{result.stdout}\n{result.stderr}"
            )

    missing_dates = discover_bronze_snapshots()
    run_dbt_transform.expand(snapshot_date=missing_dates)


silver_transform_itunes_lookup_daily()
