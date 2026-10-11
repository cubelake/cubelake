import asyncio
from dataclasses import dataclass

import httpx
from loguru import logger


@dataclass(frozen=True, slots=True)
class FetchConfig:
    batch_size: int = 10
    batch_delay_seconds: float = 4.0
    timeout_seconds: float = 15.0
    max_retries: int = 2
    retry_delay_seconds: float = 5.0


async def fetch_json(urls: list[str], config: FetchConfig = FetchConfig()) -> dict[str, dict]:
    """GET every URL in polite batches, retrying failures. Returns only the URLs that succeeded."""
    logger.info("Collecting {} URLs", len(urls))
    async with httpx.AsyncClient(
        headers={"Accept": "application/json"},
        timeout=httpx.Timeout(config.timeout_seconds),
    ) as client:
        results = await _fetch_batches(client, urls, config)

        for _ in range(config.max_retries):
            failed = [u for u, r in results.items() if r is None]
            if not failed:
                break
            logger.info("Retrying {} failed URLs", len(failed))
            await asyncio.sleep(config.retry_delay_seconds)
            results.update(await _fetch_batches(client, failed, config))

    ok = {u: r for u, r in results.items() if r is not None}
    logger.info("Collected {}/{} URLs", len(ok), len(urls))
    return ok


async def _fetch_one(client: httpx.AsyncClient, url: str) -> dict | None:
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


async def _fetch_batches(
    client: httpx.AsyncClient, urls: list[str], config: FetchConfig
) -> dict[str, dict | None]:
    results: dict[str, dict | None] = {}
    total_batches = (len(urls) + config.batch_size - 1) // config.batch_size

    for batch_idx, i in enumerate(range(0, len(urls), config.batch_size), start=1):
        batch = urls[i : i + config.batch_size]
        batch_results = await asyncio.gather(*[_fetch_one(client, u) for u in batch])
        ok = sum(1 for r in batch_results if r is not None)
        logger.info("Batch {}/{}: ok={}, failed={}", batch_idx, total_batches, ok, len(batch) - ok)
        results.update(zip(batch, batch_results, strict=True))

        if i + config.batch_size < len(urls):
            await asyncio.sleep(config.batch_delay_seconds)

    return results
