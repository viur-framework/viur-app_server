import mimetypes
import re
import time
import typing as t
from wsgiref.types import StartResponse, WSGIApplication, WSGIEnvironment

from werkzeug.http import http_date, is_resource_modified
from werkzeug.middleware.shared_data import SharedDataMiddleware
from werkzeug.utils import get_content_type
from werkzeug.wsgi import get_path_info, wrap_file


class SharedData(SharedDataMiddleware):
    """use regex to find a matching files"""

    def __init__(
        self,
        app: WSGIApplication,
        exports: (
            dict[str, str | tuple[str, str]]
            | t.Iterable[tuple[str, str | tuple[str, str]]]
        ),
        disallow: None = None,
        cache: bool = True,
        cache_timeout: int = 60 * 60 * 12,
        fallback_mimetype: str = "application/octet-stream",
    ) -> None:

        self.org_exports = exports.copy()
        super().__init__(app, exports, disallow, cache, cache_timeout,
                         fallback_mimetype)

    def __call__(
        self, environ: WSGIEnvironment, start_response: StartResponse
    ) -> t.Iterable[bytes]:
        path = get_path_info(environ)
        file_loader = None

        for search_path, loader in self.exports:
            # let's check for regex, and inject real_path
            if re.match(search_path, path):
                real_path = re.sub(search_path, self.org_exports[search_path],path, 1)
                real_filename, file_loader = self.get_file_loader(real_path)(None)

                if file_loader is not None:
                    break

            if search_path == path:
                real_filename, file_loader = loader(None)

                if file_loader is not None:
                    break

            if not search_path.endswith("/"):
                search_path += "/"

            if path.startswith(search_path):
                real_filename, file_loader = loader(path[len(search_path):])

                if file_loader is not None:
                    break

        if file_loader is None or not self.is_allowed(real_filename):  # noqa
            return self.app(environ, start_response)

        guessed_type = mimetypes.guess_type(real_filename)  # type: ignore
        mime_type = get_content_type(guessed_type[0] or self.fallback_mimetype,"utf-8")

        try:
            f, mtime, file_size = file_loader()
        except:
            return self.app(environ, start_response)  # 404

        headers = [("Date", http_date())]

        if self.cache:
            etag = self.generate_etag(mtime, file_size,
                                      real_filename)  # type: ignore
            headers += [
                ("Etag", f'"{etag}"'),
                ("Cache-Control", f"max-age={self.cache_timeout}, public"),
            ]

            if not is_resource_modified(environ, etag, last_modified=mtime):
                f.close()
                start_response("304 Not Modified", headers)
                return []

            headers.append(("Expires", http_date(time.time() + self.cache_timeout)))
        else:
            headers.append(("Cache-Control", "public"))

        headers.extend(
            (
                ("Content-Type", mime_type),
                ("Content-Length", str(file_size)),
                ("Last-Modified", http_date(mtime)),
            )
        )
        start_response("200 OK", headers)
        return wrap_file(environ, f)
