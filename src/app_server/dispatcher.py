import re
import typing as t
from wsgiref.types import StartResponse, WSGIEnvironment

from werkzeug.middleware.dispatcher import DispatcherMiddleware


class Dispatcher(DispatcherMiddleware):
    """use regex to find a matching route"""

    def __call__(
        self, environ: WSGIEnvironment, start_response: StartResponse
    ) -> t.Iterable[bytes]:
        app = self.mounts["/"]

        for route, _app in self.mounts.items():
            if re.match(route, environ["PATH_INFO"]):
                app = _app
                break
        return app(environ, start_response)
