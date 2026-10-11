from common.base_ingestor import BaseIngestor
from ingestion_apple_itunes.url_factory import UrlFactory


class Ingestor(BaseIngestor):
    def normalize(self, raw: dict) -> list[dict]:
        return [raw]

    async def collect(self, app_ids_by_key: dict[str, list[str]]) -> list[dict]:
        pairs = UrlFactory.list_all_urls_with_keys(app_ids_by_key)
        self._url_key_map = {url: key for key, url in pairs}
        urls = list(self._url_key_map)
        return await self._run_collect(urls)
