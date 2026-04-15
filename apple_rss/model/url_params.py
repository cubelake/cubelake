from enum import StrEnum


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
