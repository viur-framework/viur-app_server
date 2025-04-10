import typing as t
import urllib
from wsgiref.types import StartResponse, WSGIApplication, WSGIEnvironment
from werkzeug.middleware.http_proxy import ProxyMiddleware

class Proxy(ProxyMiddleware):
    """this addition allows to redirect all routes to given targets"""

    def __init__(
        self,
        app: WSGIApplication,
        targets: t.Mapping[str, dict[str, t.Any]],
        chunk_size: int = 2 << 13,
        timeout: int = 10,
    ) -> None:
        super().__init__(app, targets, chunk_size, timeout)

        def _set_defaults(opts):
            opts.setdefault("remove_prefix", False)
            opts.setdefault("host", "<auto>")
            opts.setdefault("headers", {})
            opts.setdefault("ssl_context", None)
            return opts

        self.targets = {
            f"{k}": _set_defaults(v) for k, v in targets.items()
        }

    def __call__(
        self, environ: WSGIEnvironment, start_response: StartResponse
    ) -> t.Iterable[bytes]:

        # Overide Pathinfo because werkzueg not unquote the path correct
        # https://github.com/pallets/werkzeug/blob/7868bef5d978093a8baa0784464ebe5d775ae92a/src/werkzeug/serving.py#L179-L208
        path =  environ["REQUEST_URI"]
        path = urllib.parse.urlparse(path).path
        app = self.app
        for prefix, opts in self.targets.items():
            if path.startswith(prefix):
                app = self.proxy_to(opts, path, prefix)
                break

        return app(environ, start_response)
