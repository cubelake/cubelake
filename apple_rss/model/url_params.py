from enum import StrEnum

from pydantic import BaseModel


# https://rss.marketingtools.apple.com/api/v2/no/apps/top-free/100/apps.json
class FeedType(StrEnum):
    TOP_FREE = "top-free"
    TOP_PAID = "top-paid"


class MediaType(StrEnum):
    APPS = "apps"


class SchemaType(StrEnum):
    APPS = "apps"


class ResponseFormat(StrEnum):
    JSON = "json"


class AppleUrlParams(BaseModel):
    country: str
    media_type: MediaType = MediaType.APPS
    feed_type: FeedType
    limit: int = 100 
    schema_type: SchemaType = SchemaType.APPS
    response_format: ResponseFormat = ResponseFormat.JSON
