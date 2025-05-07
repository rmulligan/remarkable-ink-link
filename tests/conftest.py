import httpx


# Monkey-patch httpx.Client.__init__ to accept 'app' keyword argument
_original_httpx_client_init = httpx.Client.__init__


def _patched_httpx_client_init(self, *args, **kwargs):
    # Remove 'app' if provided by starlette TestClient
    kwargs.pop("app", None)
    return _original_httpx_client_init(self, *args, **kwargs)


httpx.Client.__init__ = _patched_httpx_client_init
