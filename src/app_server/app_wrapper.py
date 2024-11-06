import typing as t
from wsgiref.types import StartResponse, WSGIEnvironment

from werkzeug.wrappers import Request, Response
class AppWrapper:
    """simple wrapping app"""

    @staticmethod
    def wsgi_app(
        environ: WSGIEnvironment, start_response: StartResponse
    ) -> t.Iterable[bytes]:
        request = Request(environ)
        response = Response(f'Path not found or invalid: {request.path}',
                            status=404)
        return response(environ, start_response)

    def __call__(
        self, environ: WSGIEnvironment, start_response: StartResponse
    ) -> t.Iterable[bytes]:
        return self.wsgi_app(environ, start_response)
