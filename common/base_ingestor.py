import asyncio

import httpx
from loguru import logger

from common.ingestion_config import IngestionConfig


class BaseIngestor:
    def __init__(self) -> None:
        self._config = IngestionConfig()
        self._url_key_map: dict[str, str] = {}

    def get_headers(self) -> dict[str, str]:
        return {"Accept": "application/json"}

    def normalize(self, raw: dict) -> list[dict]:
        raise NotImplementedError

    async def _fetch_one(self, client: httpx.AsyncClient, url: str) -> dict | None:
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.json()
            logger.warning("HTTP {} for {}", resp.status_code, url)
        except httpx.RequestError as e:
            logger.warning("Error fetching {}: {!r}", url, e)
        except ValueError as e:
            logger.warning("Invalid JSON for {}: {!r}", url, e)
        return None

    async def _fetch_batch(
        self, client: httpx.AsyncClient, urls: list[str]
    ) -> dict[str, dict | None]:
        results: dict[str, dict | None] = {}
        batch_size = self._config.batch_size
        total = len(urls)
        total_batches = (total + batch_size - 1) // batch_size

        for batch_idx, i in enumerate(range(0, total, batch_size), start=1):
            batch = urls[i : i + batch_size]
            remaining = max(total - (i + len(batch)), 0)
            logger.info(
                "Batch {}/{}: fetching {} URLs ({} remaining after this)",
                batch_idx,
                total_batches,
                len(batch),
                remaining,
            )
            batch_results = await asyncio.gather(
                *[self._fetch_one(client, u) for u in batch]
            )
            ok = sum(1 for r in batch_results if r is not None)
            failed = len(batch_results) - ok
            logger.info(
                "Batch {}/{} done: ok={}, failed={}",
                batch_idx,
                total_batches,
                ok,
                failed,
            )
            results.update(dict(zip(batch, batch_results, strict=True)))

            if i + batch_size < total:
                logger.debug(
                    "Sleeping {}s before next batch",
                    self._config.batch_delay_seconds,
                )
                await asyncio.sleep(self._config.batch_delay_seconds)

        return results

    async def _run_collect(self, urls: list[str]) -> list[dict]:
        logger.info("Collecting {} URLs", len(urls))
        timeout = httpx.Timeout(self._config.timeout_seconds)

        async with httpx.AsyncClient(
            headers=self.get_headers(), timeout=timeout
        ) as client:
            results = await self._fetch_batch(client, urls)

            for _ in range(self._config.max_retries):
                failed = [u for u, r in results.items() if r is None]
                if not failed:
                    break
                logger.info("Retrying {} failed URLs", len(failed))
                await asyncio.sleep(self._config.retry_delay_seconds)
                results.update(await self._fetch_batch(client, failed))

        records: list[dict] = []
        for url, raw in results.items():
            if raw is None:
                continue
            key = self._url_key_map[url]
            for record in self.normalize(raw):
                records.append({"preset_key": key, "url": url, "feed": record})

        logger.info("Collected {}/{} URLs", len(records), len(urls))
        return records
