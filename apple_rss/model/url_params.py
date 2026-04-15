from enum import StrEnum


class FeedType(StrEnum):
    TOP_FREE = "top-free"
    TOP_PAID = "top-paid"


class MediaType(StrEnum):
    APPS = "apps"


class SchemaType(StrEnum):
    APPS = "apps"


class ResponseFormat(StrEnum):
    JSON = "json"
