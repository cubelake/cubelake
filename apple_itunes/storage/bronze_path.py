from typing import ClassVar

from common.storage.bronze_storage_path import BaseBronzeStoragePath


class AdlsBronzeStoragePath(BaseBronzeStoragePath):
    dataset: ClassVar[str] = "appstore_itunes"
