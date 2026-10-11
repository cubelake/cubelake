from apple_itunes.model.url_builder import AppleItunesUrlBuilder
from apple_itunes.model.url_params import AppleItunesUrlParams


class UrlFactory:
    @classmethod
    def list_all_urls_with_keys(
        cls, app_ids_by_key: dict[str, list[str]]
    ) -> list[tuple[str, str]]:
        return [
            (
                preset_key,
                AppleItunesUrlBuilder.build_url(
                    AppleItunesUrlParams(
                        id=ids,
                        country=preset_key.split("_")[0],
                    )
                ),
            )
            for preset_key, ids in app_ids_by_key.items()
            if ids
        ]
