BASE_URL = "https://itunes.apple.com/lookup"


# https://itunes.apple.com/lookup?id=324684580,544007664,310633997&country=no
def lookup_url(app_ids: list[str], country: str) -> str:
    return f"{BASE_URL}?id={','.join(app_ids)}&country={country}"


def lookup_urls(app_ids_by_key: dict[str, list[str]]) -> dict[str, str]:
    """preset_key (e.g. `no_top_free`) -> lookup URL. Keys without app ids are skipped."""
    return {
        key: lookup_url(ids, key.split("_")[0])
        for key, ids in app_ids_by_key.items()
        if ids
    }
