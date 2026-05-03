import json
import os
import subprocess

import duckdb
from airflow.sdk import Asset, dag, task
from airflow.sdk.exceptions import AirflowSkipException
from azure.storage.filedatalake import DataLakeServiceClient
from common.storage.azure_tokens import AppstoreSilverToken, GoldToken
from common.storage.containers import ADLS_GOLD_CONTAINER, ADLS_SILVER_CONTAINER

from dags.silver.appstore.transform_appstore_apps_daily import SILVER_APPSTORE_APPS
from dags.utils.default_args import gold_args

DBT_PROJECT_DIR = os.environ.get("DBT_PROJECT_DIR", "/opt/airflow/dbt/appstore-transform")

GOLD_APPSTORE_BIWEEKLY = Asset("azure://gold/appstore/biweekly")

GOLD_PREFIX = "appstore/biweekly"
DBT_MODEL = "gold_app_worldwide_biweekly"


@dag(
    dag_id="gold_transform_appstore_biweekly",
    default_args=gold_args,
    schedule=[SILVER_APPSTORE_APPS],
    max_active_runs=1,
    catchup=False,
    tags=["gold", "appstore", "biweekly", "transform"],
)
def gold_transform_appstore_biweekly():
    @task(task_id="discover_missing_snapshots")
    def discover_missing_snapshots() -> list[str]:
        appstore_silver = AppstoreSilverToken()
        gold = GoldToken()

        dls_client = DataLakeServiceClient(
            account_url=appstore_silver.account_url,
            credential=appstore_silver.sas_token,
        )
        fs = dls_client.get_file_system_client(ADLS_SILVER_CONTAINER)
        silver_dates = sorted(
            p.name.split("snapshot_date=")[-1]
            for p in fs.get_paths("appstore", recursive=False)
            if p.is_directory and "snapshot_date=" in p.name
        )

        missing = []
        with duckdb.connect() as con:
            gold.init_connection(con)
            for snap in silver_dates:
                try:
                    cnt = con.execute(
                        f"SELECT COUNT(*) FROM read_parquet("
                        f"'azure://{ADLS_GOLD_CONTAINER}/{GOLD_PREFIX}/"
                        f"snapshot_date={snap}/*.parquet');"
                    ).fetchone()
                    if not cnt or cnt[0] == 0:
                        missing.append(snap)
                except duckdb.IOException:
                    missing.append(snap)

        if not missing:
            raise AirflowSkipException(f"All silver snapshots already processed into gold/{GOLD_PREFIX}")

        return missing

    @task(task_id="run_dbt_transform", max_active_tis_per_dagrun=2)
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
                "--select", DBT_MODEL,
                "--vars", json.dumps({"snapshot_date": snapshot_date}),
                "--project-dir", DBT_PROJECT_DIR,
                "--profiles-dir", DBT_PROJECT_DIR,
                "--target-path", f"/tmp/dbt_gold_biweekly_{snapshot_date}",
            ],
            env=env,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"dbt run failed for {snapshot_date}:\n{result.stdout}\n{result.stderr}")

    @task(task_id="emit_gold_biweekly_asset", outlets=[GOLD_APPSTORE_BIWEEKLY])
    def emit_gold_biweekly_asset(results: list) -> None:
        pass

    missing_dates = discover_missing_snapshots()
    dbt_done = run_dbt_transform.expand(snapshot_date=missing_dates)
    emit_gold_biweekly_asset(dbt_done)


gold_transform_appstore_biweekly()
