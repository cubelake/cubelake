from pydantic import BaseModel

from apple_rss.model.metadata import BronzeMetadata


class BronzeRow(BaseModel):
    feed: dict
    metadata: BronzeMetadata

    @classmethod
    def create(cls, feed: dict, metadata: BronzeMetadata) -> "BronzeRow":
        return cls(feed=feed, metadata=metadata)
