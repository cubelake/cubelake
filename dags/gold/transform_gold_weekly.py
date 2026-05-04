import os
import subprocess

from airflow.sdk import Asset, dag, task
from common.storage.azure_tokens import AppstoreSilverToken, GoldToken

from dags.gold.transform_gold_daily import GOLD_APPSTORE_DAILY
from dags.utils.default_args import gold_args

DBT_PROJECT_DIR = os.environ.get("DBT_PROJECT_DIR", "/opt/airflow/dbt/appstore-transform")

GOLD_DIM_APPS = Asset("azure://gold/dim_apps")


@dag(
    dag_id="gold_transform_dim_apps",
    default_args=gold_args,
    schedule=[GOLD_APPSTORE_DAILY],
    max_active_runs=1,
    catchup=False,
    tags=["gold", "apps", "transform", "dim"],
)
def gold_transform_weekly():
    @task(task_id="run_dbt_dim_apps")
    def run_dbt_dim_apps() -> None:
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
                "--select", "gold_dim_apps",
                "--project-dir", DBT_PROJECT_DIR,
                "--profiles-dir", DBT_PROJECT_DIR,
                "--target-path", "/tmp/dbt_target_gold_dim_apps",
            ],
            env=env,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"dbt gold_dim_apps failed:\n{result.stdout}\n{result.stderr}")

    @task(task_id="emit_gold_dim_apps_asset", outlets=[GOLD_DIM_APPS])
    def emit_gold_dim_apps_asset(_: None) -> None:
        pass

    emit_gold_dim_apps_asset(run_dbt_dim_apps())


gold_transform_weekly()
