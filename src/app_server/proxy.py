from werkzeug.middleware.http_proxy import ProxyMiddleware
from werkzeug.wsgi import get_path_info
import typing as t

class Proxy(ProxyMiddleware):
    """this addition allows to redirect all routes to given targets"""

    def __init__(self, app, targets, chunk_size=2 << 13, timeout=10):
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

    def __call__(self, environ: "WSGIEnvironment",
                 start_response: "StartResponse") -> t.Iterable[bytes]:
        path = get_path_info(environ, charset='utf-8', errors='replace')
        app = self.app
        for prefix, opts in self.targets.items():
            if path.startswith(prefix):
                app = self.proxy_to(opts, path, prefix)
                break

        return app(environ, start_response)
