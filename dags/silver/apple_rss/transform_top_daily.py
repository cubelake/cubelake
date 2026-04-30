import json
import os
import subprocess

import duckdb
from airflow.sdk import Asset, dag, task
from airflow.sdk.exceptions import AirflowSkipException
from apple_rss.storage import RssBronzeToken, RssSilverToken
from apple_rss.storage.containers import ADLS_BRONZE_CONTAINER, ADLS_SILVER_CONTAINER

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

        with duckdb.connect() as con:
            bronze.init_connection(con)
            bronze_dates = [
                str(row[0])
                for row in con.execute(
                    f"SELECT DISTINCT snapshot_date "
                    f"FROM read_json_auto("
                    f"'azure://{ADLS_BRONZE_CONTAINER}/appstore_rss/**/*.json'"
                    f") ORDER BY snapshot_date;"
                ).fetchall()
            ]

        missing: list[str] = []
        with duckdb.connect() as con:
            silver.init_connection(con)
            for snap in bronze_dates:
                try:
                    cnt = con.execute(
                        f"SELECT COUNT(*) FROM read_parquet("
                        f"'azure://{ADLS_SILVER_CONTAINER}/appstore_rss/"
                        f"snapshot_date={snap}/**/*.parquet');"
                    ).fetchone()
                    if not cnt or cnt[0] == 0:
                        missing.append(snap)
                except duckdb.IOException:
                    missing.append(snap)

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
