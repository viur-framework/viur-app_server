import time
import typing as t

from werkzeug._internal import _logger  # noqa
from werkzeug.serving import WSGIRequestHandler, _ansi_style, \
    _log_add_style
from werkzeug.urls import uri_to_iri

import logging


class CustomWSGIRequestHandler(WSGIRequestHandler):
    @staticmethod
    def log_date_time_string():
        """Return the current time formatted for logging."""
        now = time.time()
        year, month, day, hh, mm, ss, x, y, z = time.localtime(now)
        s = "%04d-%02d-%02d %02d:%02d:%02d" % (
            year, month, day, hh, mm, ss)
        return s

    def log_request(
        self,
        code: t.Union[int, str] = "-",
        size: t.Union[int, str] = "-",
    ) -> None:
        """coloring the status code"""
        try:
            path = uri_to_iri(self.path)
            msg = f"[{self.command}] {path}"
        except AttributeError:
            # path isn't set if the requestline was bad
            msg = self.requestline

        code = str(code)

        log_type = "info"
        if code != "200":  # possibility to filter 200 requests
            log_type = "warning"

        if _log_add_style:
            if code[0] == "1":  # 1xx - Informational
                code = _ansi_style(code, "bold")
            elif code == "200":  # 2xx - Success
                pass
            elif code == "304":  # 304 - Resource Not Modified
                code = _ansi_style(code, "cyan")
            elif code[0] == "3":  # 3xx - Redirection
                code = _ansi_style(code, "green")
            elif code == "404":  # 404 - Resource Not Found
                code = _ansi_style(code, "yellow")
            elif code[0] == "4":  # 4xx - Client Error
                code = _ansi_style(code, "bold", "red")
            else:  # 5xx, or any other response
                code = _ansi_style(code, "bold", "red")

        self.log(log_type, '[%s] %s', code, msg)

    def log(self, log_type: str, message: str, *args) -> None:
        global _logger

        if _logger is None:
            _logger = logging.getLogger("werkzeug")
            _logger.setLevel(logging.INFO)
            _logger.addHandler(logging.StreamHandler())

        getattr(_logger, log_type)(f"[{self.log_date_time_string()}] {message % args}")
