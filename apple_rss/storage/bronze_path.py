from pydantic import BaseModel


class AdlsBronzeStoragePath(BaseModel):
    snapshot_date: str
    country: str
    feed_type: str

    @property
    def directory(self) -> str:
        return f"appstore_rss/snapshot_date={self.snapshot_date}/"

    @property
    def file_name(self) -> str:
        return f"{self.country.lower()}_{self.feed_type}.json"
