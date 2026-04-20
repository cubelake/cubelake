import asyncio
import json
import os
from datetime import date
from typing import Any, cast

from airflow.sdk import Asset, dag, task
from apple_rss.model.bronze_row import BronzeRow
from apple_rss.model.metadata import BronzeMetadata
from azure.storage.filedatalake import DataLakeServiceClient
from ingestion_apple_rss.ingestor import Ingestor

from dags.utils.adls_containers import ADLS_BRONZE_CONTAINER, AdlsBronzeStoragePath
from dags.utils.default_args import bronze_args

BRONZE_APPSTORE_RSS = Asset("azure://bronze/appstore_rss")


@dag(
    dag_id="bronze_top_country_pipeline",
    default_args=bronze_args,
    schedule="@daily",
    max_active_runs=1,
    catchup=False,
    tags=["bronze", "country", "rss", "daily"],
)
def bronze_top_country_pipeline() -> None:
    @task(task_id="collect_data")
    def collect_data() -> list[dict]:
        collector = Ingestor()
        return asyncio.run(collector.collect())

    @task(task_id="build_bronze_rows")
    def build_bronze_rows(data: Any) -> list[dict]:
        data_typed = cast(list[dict], data)
        source = "ingestion-apple"
        return [
            BronzeRow.create(
                feed=item.get("feed") or {},
                metadata=BronzeMetadata.create(
                    source=source, preset_key=item.get("preset_key", "")
                ),
            ).model_dump(by_alias=True)
            for item in data_typed
        ]

    @task(task_id="load_to_adls", outlets=[BRONZE_APPSTORE_RSS])
    def load_to_adls(rows: Any) -> None:
        rows_typed = cast(list[dict], rows)

        try:
            account_url = os.environ["ACCOUNT_URL"]
            sas_token = os.environ["BRONZE_SAS_TOKEN"]
        except KeyError as e:
            raise RuntimeError(f"Required environment variable not set: {e}") from e

        service_client = DataLakeServiceClient(
            account_url=account_url,
            credential=sas_token,
        )
        snapshot_date = date.today().isoformat()
        file_system = service_client.get_file_system_client(ADLS_BRONZE_CONTAINER)

        for row in rows_typed:
            path = AdlsBronzeStoragePath(
                snapshot_date=snapshot_date,
                country=row["_country"],
                feed_type=row["_feed_type"],
            )

            directory_client = file_system.get_directory_client(path.directory)
            file_client = directory_client.get_file_client(path.file_name)
            data = (json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8")
            file_client.upload_data(data, overwrite=True)

    data = collect_data()
    rows = build_bronze_rows(data)
    load_to_adls(rows)


bronze_apple_rss_dag = bronze_top_country_pipeline()
