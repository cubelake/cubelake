import json
import os
import subprocess

from airflow.sdk import Asset, dag, task
from airflow.sdk.exceptions import AirflowSkipException
from azure.storage.filedatalake import DataLakeServiceClient
from common.storage.azure_tokens import AppstoreSilverToken, ItunesSilverToken, RssSilverToken
from common.storage.containers import ADLS_SILVER_CONTAINER

from dags.silver.apple_itunes.transform_lookup_daily import SILVER_APPSTORE_ITUNES
from dags.silver.apple_rss.transform_top_daily import SILVER_APPSTORE_RSS
from dags.utils.default_args import silver_args

DBT_PROJECT_DIR = os.environ.get("DBT_PROJECT_DIR", "/opt/airflow/dbt/appstore-transform")

SILVER_APPSTORE_APPS = Asset("azure://silver/appstore")


@dag(
    dag_id="silver_transform_appstore_apps_daily",
    default_args=silver_args,
    schedule=[SILVER_APPSTORE_RSS, SILVER_APPSTORE_ITUNES],
    max_active_runs=1,
    catchup=False,
    tags=["silver", "apps", "appstore", "transform", "daily"],
)
def silver_transform_appstore_apps_daily():
    @task(task_id="discover_missing_snapshots")
    def discover_missing_snapshots() -> list[str]:
        rss_silver = RssSilverToken()
        itunes_silver = ItunesSilverToken()
        appstore_silver = AppstoreSilverToken()

        def _snapshot_dates(client: DataLakeServiceClient, container: str, prefix: str) -> set[str]:
            fs = client.get_file_system_client(container)
            return {
                p.name.split("snapshot_date=")[-1]
                for p in fs.get_paths(prefix, recursive=False)
                if p.is_directory and "snapshot_date=" in p.name
            }

        rss_client = DataLakeServiceClient(account_url=rss_silver.account_url, credential=rss_silver.sas_token)
        itunes_client = DataLakeServiceClient(account_url=itunes_silver.account_url, credential=itunes_silver.sas_token)
        appstore_client = DataLakeServiceClient(account_url=appstore_silver.account_url, credential=appstore_silver.sas_token)

        rss_dates = _snapshot_dates(rss_client, ADLS_SILVER_CONTAINER, "appstore_rss")
        itunes_dates = _snapshot_dates(itunes_client, ADLS_SILVER_CONTAINER, "appstore_itunes")
        appstore_dates = _snapshot_dates(appstore_client, ADLS_SILVER_CONTAINER, "appstore")

        ready = rss_dates & itunes_dates
        missing = sorted(ready - appstore_dates)

        if not missing:
            raise AirflowSkipException("All snapshots already processed into silver/appstore")

        return missing

    @task(task_id="run_dbt_transform", max_active_tis_per_dagrun=4)
    def run_dbt_transform(snapshot_date: str) -> None:
        rss_silver = RssSilverToken()
        itunes_silver = ItunesSilverToken()
        appstore_silver = AppstoreSilverToken()
        account_name = rss_silver.account_url.split("://")[1].split(".")[0]

        env = {
            **os.environ,
            "ACCOUNT_NAME": account_name,
            "SILVER_SAS_TOKEN": appstore_silver.sas_token,
            "SILVER_RSS_SAS_TOKEN": rss_silver.sas_token,
            "SILVER_ITUNES_SAS_TOKEN": itunes_silver.sas_token,
        }
        result = subprocess.run(
            [
                "dbt", "run",
                "--select", "silver_appstore_apps",
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

    @task(task_id="emit_silver_appstore_asset", outlets=[SILVER_APPSTORE_APPS])
    def emit_silver_appstore_asset(results: list) -> None:
        pass

    missing_dates = discover_missing_snapshots()
    dbt_done = run_dbt_transform.expand(snapshot_date=missing_dates)
    emit_silver_appstore_asset(dbt_done)


silver_transform_appstore_apps_daily()
