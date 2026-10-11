import asyncio
import json
from typing import Any

from airflow.sdk import Asset, dag, get_current_context, task
from apple_rss.storage import RssBronzeToken
from apple_rss.storage.bronze_path import AdlsBronzeStoragePath
from apple_rss.storage.bronze_row import BronzeRow
from azure.storage.filedatalake import DataLakeDirectoryClient
from common.storage.containers import ADLS_BRONZE_CONTAINER
from ingestion_apple_rss.ingestor import Ingestor

from dags.utils.default_args import bronze_args
from dags.utils.logging import configure_loguru

configure_loguru()

BRONZE_APPSTORE_RSS = Asset("azure://bronze/appstore_rss")
SOURCE_NAME = "ingestion-apple-rss"


@dag(
    dag_id="bronze_top_daily",
    default_args=bronze_args,
    schedule="@daily",
    max_active_runs=1,
    catchup=False,
    tags=["bronze", "country", "rss", "daily"],
)
def bronze_top_daily() -> None:
    @task(task_id="collect_data")
    def collect_data() -> int:
        token = RssBronzeToken()

        context = get_current_context()
        logical_date = context.get("logical_date") or context.get("data_interval_start")
        if logical_date is None:
            raise RuntimeError("No execution date available in context")
        snapshot_date = logical_date.date().isoformat()

        results = asyncio.run(Ingestor().collect())

        base_dir = DataLakeDirectoryClient(
            account_url=token.account_url,
            file_system_name=ADLS_BRONZE_CONTAINER,
            directory_name="appstore_rss",
            credential=token.sas_token,
        )
        snapshot_dir = base_dir.get_sub_directory_client(f"snapshot_date={snapshot_date}")

        for item in results:
            bronze_row = BronzeRow.from_raw(
                feed=item.get("feed") or {},
                source=SOURCE_NAME,
                preset_key=item.get("preset_key", ""),
            )
            path = AdlsBronzeStoragePath(
                snapshot_date=snapshot_date,
                **bronze_row.path_coords.model_dump(),
            )
            file_client = snapshot_dir.get_file_client(path.file_name)
            payload = (json.dumps(bronze_row.to_record(), ensure_ascii=False) + "\n").encode("utf-8")
            file_client.upload_data(payload, overwrite=True)

        return len(results)

    @task(task_id="load_to_adls", outlets=[BRONZE_APPSTORE_RSS])
    def load_to_adls(files_written: Any) -> None:
        pass

    files_written = collect_data()
    load_to_adls(files_written)


bronze_dag = bronze_top_daily()
