from common.base_ingestor import BaseIngestor
from ingestion_apple_rss.url_factory import UrlFactory


class Ingestor(BaseIngestor):
    def get_urls(self) -> list[str]:
        pairs = UrlFactory.list_all_urls_with_keys()
        self._url_key_map = {url: key for key, url in pairs}
        return list(self._url_key_map)

    def normalize(self, raw: dict) -> list[dict]:
        return [raw.get("feed") or {}]

    async def collect(self) -> list[dict]:
        urls = self.get_urls()
        return await self._run_collect(urls)
