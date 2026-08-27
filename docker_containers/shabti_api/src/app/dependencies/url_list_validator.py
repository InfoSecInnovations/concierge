from ..functionality.loaders.url_guard import check_url_allowed


class UrlListValidator:
    async def __call__(self, urls: list[str]):
        # the URLs are caller supplied and the route only requires the update scope, so they are
        # checked here rather than in the loader: errors can't be reported once the response has
        # started streaming
        for url in urls:
            await check_url_allowed(url)
