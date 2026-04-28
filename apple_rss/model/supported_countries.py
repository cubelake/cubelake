import json
from importlib.resources import files

import pycountry
from loguru import logger


class SupportedCountries:
    FILE_NAME = "ISO-3166-1-alpha-2-VA.json"

    @classmethod
    def load_countries(cls) -> tuple[str, ...]:
        resource = files("apple_rss.data_schema").joinpath(cls.FILE_NAME)
        if resource.is_file():
            return tuple(json.loads(resource.read_text(encoding="utf-8")))
        else:
            logger.warning(f"Country file {cls.FILE_NAME} not found, using pycountry")
            return tuple(c.alpha_2.lower() for c in pycountry.countries)
