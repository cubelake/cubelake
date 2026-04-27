from typing import ClassVar

from pydantic import BaseModel


class BaseBronzeStoragePath(BaseModel):
    dataset: ClassVar[str]
    snapshot_date: str
    country: str
    feed_type: str

    @property
    def directory(self) -> str:
        return f"{self.dataset}/snapshot_date={self.snapshot_date}/"

    @property
    def file_name(self) -> str:
        return f"{self.country.lower()}_{self.feed_type}.json"
