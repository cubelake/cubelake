from enum import StrEnum

from pydantic import BaseModel


class FeedType(StrEnum):
    TOP_FREE = "top-free"
    TOP_PAID = "top-paid"


class MediaType(StrEnum):
    APPS = "apps"


class SchemaType(StrEnum):
    APPS = "apps"


class ResponseFormat(StrEnum):
    JSON = "json"


# https://rss.marketingtools.apple.com/api/v2/no/apps/top-free/100/apps.json
class AppleUrlParams(BaseModel):
    country: str
    media_type: MediaType = MediaType.APPS
    feed_type: FeedType
    limit: int
    schema_type: SchemaType = SchemaType.APPS
    response_format: ResponseFormat = ResponseFormat.JSON


class AppleUrlBuilder:
    BASE_URL = "https://rss.marketingtools.apple.com/api/v2"

    @classmethod
    def build_url(cls, params: AppleUrlParams) -> str:
        return (
            f"{cls.BASE_URL}/"
            f"{params.country}/"
            f"{params.media_type.value}/"
            f"{params.feed_type.value}/"
            f"{params.limit}/"
            f"{params.schema_type.value}."
            f"{params.response_format.value}"
        )
