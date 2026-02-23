import logging
import urllib.request
import urllib.error
from wsgiref.types import StartResponse, WSGIApplication, WSGIEnvironment

from werkzeug.wrappers import Request

logger = logging.getLogger(__name__)

CHUNK_SIZE = 64 * 1024  # 64 KB


class ForwardProxy:
    """WSGI middleware that forwards matching requests to an external server.

    Used to proxy requests (e.g. file downloads) to a production server
    during local development, where those resources don't exist locally.

    Responses are streamed chunk-wise so large files don't consume memory.
    """

    def __init__(self, app: WSGIApplication, target_url: str) -> None:
        self.app = app
        self.target_url = target_url.rstrip("/")

    def __call__(
        self, environ: WSGIEnvironment, start_response: StartResponse
    ):
        request = Request(environ)
        target = self.target_url + request.path
        if request.query_string:
            target += "?" + request.query_string.decode()

        try:
            req = urllib.request.Request(target, method=request.method)
            resp = urllib.request.urlopen(req, timeout=30)
            headers = [(k, v) for k, v in resp.headers.items()]
            start_response(f"{resp.status} {resp.reason}", headers)
            return self._iter_response(resp)
        except Exception as exc:
            logger.debug("ForwardProxy failed for %s: %s", target, exc)
            return self.app(environ, start_response)

    @staticmethod
    def _iter_response(resp):
        """Yield response body in chunks to support large files."""
        try:
            while chunk := resp.read(CHUNK_SIZE):
                yield chunk
        finally:
            resp.close()
