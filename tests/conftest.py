import httpx


# Monkey-patch httpx.Client.__init__ to accept 'app' keyword argument.
# This patch is necessary to ensure compatibility with starlette's TestClient,
# which passes an 'app' keyword argument to httpx.Client. The 'app' argument
# is not recognized by httpx.Client and would otherwise raise an error.
# By removing the 'app' argument before calling the original __init__ method,
# we allow the TestClient to function correctly. Note that this patch relies
# on the internal behavior of httpx.Client, which may change in future versions.
# If httpx is updated, this patch should be reviewed for compatibility.
_original_httpx_client_init = httpx.Client.__init__


def _patched_httpx_client_init(self, *args, **kwargs):
    # Remove 'app' if provided by starlette TestClient
    kwargs.pop("app", None)
    return _original_httpx_client_init(self, *args, **kwargs)


httpx.Client.__init__ = _patched_httpx_client_init
