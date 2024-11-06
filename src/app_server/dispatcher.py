import re
from werkzeug.middleware.dispatcher import DispatcherMiddleware


class Dispatcher(DispatcherMiddleware):
    """use regex to find a matching route"""

    def __call__(self, environ, start_response):
        app = self.mounts["/"]

        for route, _app in self.mounts.items():
            if re.match(route, environ["PATH_INFO"]):
                app = _app
                break
        return app(environ, start_response)
