from apple_itunes.model.url_params import AppleItunesUrlParams


# https://itunes.apple.com/lookup?id=324684580,544007664,310633997&country=no
class AppleItunesUrlBuilder:
    BASE_URL = "https://itunes.apple.com/lookup"

    @classmethod
    def build_url(cls, params: AppleItunesUrlParams) -> str:
        ids = ",".join(params.id)
        return f"{cls.BASE_URL}?id={ids}&country={params.country}"


# params = AppleItunesUrlParams(id=["324684580", "544007664", "310633997"], country="no")

# url = AppleItunesUrlBuilder.build_url(params)
# print(url)
# # https://itunes.apple.com/lookup?id=324684580,544007664,310633997&country=no

