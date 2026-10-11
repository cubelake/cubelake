import asyncio
import json

import duckdb
from airflow.sdk import Asset, dag, task
from airflow.sdk.exceptions import AirflowSkipException
from apple_itunes.storage import ItunesBronzeToken
from apple_rss.storage import RssSilverToken
from dags.silver.apple_rss.transform_top_daily import SILVER_APPSTORE_RSS
from apple_itunes.storage.bronze_path import AdlsBronzeStoragePath
from apple_itunes.storage.bronze_row import BronzeRow
from azure.storage.filedatalake import DataLakeDirectoryClient, DataLakeServiceClient
from common.storage.containers import ADLS_BRONZE_CONTAINER, ADLS_SILVER_CONTAINER
from ingestion_apple_itunes.ingestor import Ingestor

from dags.utils.default_args import bronze_args
from dags.utils.logging import configure_loguru

BRONZE_APPSTORE_ITUNES = Asset("azure://bronze/appstore_itunes")
SOURCE_NAME = "ingestion-apple-itunes"


@dag(
    dag_id="bronze_itunes_lookup_daily",
    default_args=bronze_args,
    schedule=[SILVER_APPSTORE_RSS],
    max_active_runs=1,
    catchup=False,
    tags=["bronze", "country", "itunes", "daily"],
)
def bronze_itunes_lookup_daily() -> None:
    @task(task_id="discover_unprocessed_snapshots")
    def discover_unprocessed_snapshots() -> list[str]:
        configure_loguru()
        silver = RssSilverToken()
        bronze = ItunesBronzeToken()

        with duckdb.connect() as con:
            silver.init_connection(con)
            silver_dates = [
                str(row[0])
                for row in con.execute(
                    f"SELECT DISTINCT snapshot_date "
                    f"FROM read_parquet("
                    f"  'azure://{ADLS_SILVER_CONTAINER}/appstore_rss/**/*.parquet',"
                    f"  hive_partitioning = true"
                    f") ORDER BY snapshot_date;"
                ).fetchall()
            ]

        fs = DataLakeServiceClient(
            account_url=bronze.account_url, credential=bronze.sas_token
        ).get_file_system_client(ADLS_BRONZE_CONTAINER)
        bronze_dates: set[str] = {
            p.name.split("snapshot_date=")[-1]
            for p in fs.get_paths("appstore_itunes", recursive=False)
            if p.is_directory and "snapshot_date=" in p.name
        }

        missing = [d for d in silver_dates if d not in bronze_dates]

        if not missing:
            raise AirflowSkipException("All silver RSS snapshots already ingested into bronze iTunes")

        return missing

    @task(task_id="collect_data", max_active_tis_per_dagrun=1)
    def collect_data(snapshot_date: str) -> int:
        configure_loguru()
        silver = RssSilverToken()
        token = ItunesBronzeToken()

        with duckdb.connect() as con:
            silver.init_connection(con)
            rows = con.execute(
                f"SELECT country, feed_type, app_id "
                f"FROM read_parquet("
                f"  'azure://{ADLS_SILVER_CONTAINER}/appstore_rss/**/*.parquet',"
                f"  hive_partitioning = true"
                f") "
                f"WHERE snapshot_date = '{snapshot_date}' "
                f"AND app_id IS NOT NULL "
                f"ORDER BY app_rank;"
            ).fetchall()

        ids: dict[str, list[str]] = {}
        for country, feed_type, app_id in rows:
            key = f"{country.lower()}_top_{feed_type.lower()}"
            ids.setdefault(key, []).append(str(app_id))

        results = asyncio.run(Ingestor().collect(ids))

        base_dir = DataLakeDirectoryClient(
            account_url=token.account_url,
            file_system_name=ADLS_BRONZE_CONTAINER,
            directory_name="appstore_itunes",
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

    @task(task_id="load_to_adls", outlets=[BRONZE_APPSTORE_ITUNES])
    def load_to_adls(files_written: list[int]) -> None:
        pass

    missing_dates = discover_unprocessed_snapshots()
    files_written = collect_data.expand(snapshot_date=missing_dates)
    load_to_adls(files_written)


bronze_dag = bronze_itunes_lookup_daily()
