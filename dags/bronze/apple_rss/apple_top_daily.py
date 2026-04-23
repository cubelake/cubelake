import asyncio
import json
import os
from typing import Any, cast

from airflow.sdk import Asset, dag, get_current_context, task
from apple_rss.model.bronze_row import BronzeRow
from apple_rss.storage.bronze_path import AdlsBronzeStoragePath
from apple_rss.storage.containers import ADLS_BRONZE_CONTAINER
from azure.storage.filedatalake import DataLakeServiceClient
from ingestion_apple_rss.ingestor import Ingestor

from dags.utils.default_args import bronze_args
from dags.utils.logging import configure_loguru

configure_loguru()

BRONZE_APPSTORE_RSS = Asset("azure://bronze/appstore_rss")
SOURCE_NAME = "ingestion-apple"


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
    def collect_data() -> list[dict]:
        collector = Ingestor()
        return asyncio.run(collector.collect())

    @task(task_id="build_bronze_rows")
    def build_bronze_rows(data: Any) -> list[dict]:
        data_typed = cast(list[dict], data)
        rows = []
        for item in data_typed:
            bronze_row = BronzeRow.from_raw(
                feed=item.get("feed") or {},
                source=SOURCE_NAME,
                preset_key=item.get("preset_key", ""),
            )
            rows.append(
                {
                    "record": bronze_row.to_record(),
                    "path_coords": bronze_row.path_coords.model_dump(),
                }
            )
        return rows

    @task(task_id="load_to_adls", outlets=[BRONZE_APPSTORE_RSS])
    def load_to_adls(rows: Any) -> None:
        rows_typed = cast(list[dict], rows)

        try:
            account_url = os.environ["ACCOUNT_URL"]
            sas_token = os.environ["BRONZE_SAS_TOKEN"]
        except KeyError as e:
            raise RuntimeError(f"Required environment variable not set: {e}") from e

        context = get_current_context()
        data_interval_start = context["data_interval_start"]
        if data_interval_start is None:
            raise RuntimeError("data_interval_start is not available in context")
        snapshot_date = data_interval_start.date().isoformat()

        service_client = DataLakeServiceClient(
            account_url=account_url,
            credential=sas_token,
        )
        file_system = service_client.get_file_system_client(ADLS_BRONZE_CONTAINER)

        for row in rows_typed:
            path = AdlsBronzeStoragePath(
                snapshot_date=snapshot_date,
                **row["path_coords"],
            )
            directory_client = file_system.get_directory_client(path.directory)
            file_client = directory_client.get_file_client(path.file_name)
            data = (json.dumps(row["record"], ensure_ascii=False) + "\n").encode(
                "utf-8"
            )
            file_client.upload_data(data, overwrite=True)

    data = collect_data()
    rows = build_bronze_rows(data)
    load_to_adls(rows)


bronze_dag = bronze_top_daily()
