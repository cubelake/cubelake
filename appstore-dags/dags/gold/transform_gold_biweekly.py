import os
import subprocess

from airflow.sdk import Asset, dag, task
from common.storage.azure_tokens import AppstoreSilverToken, GoldToken

from dags.utils.default_args import gold_args

DBT_PROJECT_DIR = os.environ.get("DBT_PROJECT_DIR", "/opt/airflow/dbt/appstore-transform")

GOLD_FCT_RANK_HISTORY = Asset("azure://gold/fct_app_rank_history")


@dag(
    dag_id="gold_transform_biweekly",
    default_args=gold_args,
    schedule="0 4 1,15 * *",  # 1st and 15th of each month at 04:00
    max_active_runs=1,
    catchup=False,
    tags=["gold", "apps", "transform", "biweekly", "history"],
)
def gold_transform_biweekly():
    @task(task_id="run_dbt_rank_history")
    def run_dbt_rank_history() -> None:
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
                "--select", "gold_fct_app_rank_history",
                "--project-dir", DBT_PROJECT_DIR,
                "--profiles-dir", DBT_PROJECT_DIR,
                "--target-path", "/tmp/dbt_target_gold_rank_history",
            ],
            env=env,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"dbt gold_fct_app_rank_history failed:\n{result.stdout}\n{result.stderr}")

    @task(task_id="emit_gold_rank_history_asset", outlets=[GOLD_FCT_RANK_HISTORY])
    def emit_gold_rank_history_asset(_: None) -> None:
        pass

    emit_gold_rank_history_asset(run_dbt_rank_history())


gold_transform_biweekly()
