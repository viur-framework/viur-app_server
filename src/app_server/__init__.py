import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml
from werkzeug._internal import _logger  # noqa
from werkzeug.serving import run_simple

from . import utils
from .app_wrapper import AppWrapper
from .dispatcher import Dispatcher
from .proxy import Proxy
from .request_handler import CustomWSGIRequestHandler
from .shared_data import SharedData

__version__ = "0.1.0"

subprocesses = []


def start_server(
    host: str,
    port: int,
    gunicorn_port: int,
    app_folder: Path,
    app_yaml: dict,
    timeout: int,
    protocol: str = "http",
) -> None:
    """use the dispatcherMiddleware to connect SharedDataMiddleware and ProxyMiddleware with the wrapping app."""
    app = AppWrapper()
    apps = {}
    # make shared middlewares for static files as configured in app.yaml
    for route in app_yaml["handlers"]:
        if path := route.get("static_dir"):
            pattern = route["url"] + "/.*"

        elif path := route.get("static_files"):
            pattern = route["url"]

        else:
            continue  # skip

        # print(pattern, route["url"], path)
        apps[pattern] = SharedData(
            app.wsgi_app, {route["url"]: os.path.join(app_folder, path)}
        )

    apps["/"] = Proxy(
        app.wsgi_app,
        {
            "/": {
                "target": f"{protocol}://{host}:{gunicorn_port}/",
                "host": None
            }
        },
        timeout=timeout
    )
    app.wsgi_app = Dispatcher(app.wsgi_app, apps)

    run_simple(host, port, app, use_debugger=False, use_reloader=True,
               threaded=True, request_handler=CustomWSGIRequestHandler)


def start_gunicorn(
    args: argparse.Namespace,
    app_yaml: dict,
    app_folder: Path,
) -> None:
    # Gunicorn call command
    if not (entrypoint := args.entrypoint):
        entrypoint = app_yaml.get(
            "entrypoint",
            f"gunicorn -b :$PORT --disable-redirect-access-to-syslog main:app"
        )
    entrypoint = entrypoint.replace(f"$PORT", str(args.gunicorn_port))
    # Remove -w / --workers / --threads arguments,
    # we set them later with the values from our argparser
    entrypoint = re.sub(r"\s+-(w|-workers|-threads)\s+\d+", " ", entrypoint)

    entrypoint = entrypoint.split()
    entrypoint.extend(["--workers", str(args.workers)])
    entrypoint.extend(["--threads", str(args.threads)])

    if "--reload" not in entrypoint:
        entrypoint.insert(1, "--reload")
    if "--reuse-port" not in entrypoint:
        entrypoint.insert(1, "--reuse-port")

    entrypoint.extend(["--timeout", str(args.timeout)])

    subprocesses.append(subprocess.Popen(entrypoint, cwd=app_folder))


def main():
    """main entrypoint

    collect parameters
    set environment variables
    start gunicorn
    start wrapping app
    """
    argument_parser = argparse.ArgumentParser(
        description="alternative dev_appserver",
        epilog=f"Version: {__version__}"
    )

    argument_parser.add_argument(
        "distribution_folder",
        help="Path of the application"
    )
    argument_parser.add_argument(
        "--appyaml",
        default="app.yaml",
        help="Path to app.yaml file (relative to the distribution_folder)"
    )
    argument_parser.add_argument(
        '-A', '--application',
        action='store',
        dest='app_id',
        required=True,
        help='Set the application id'
    )
    argument_parser.add_argument(
        '--host',
        default="localhost",
        help='host name to which application modules should bind'
    )
    argument_parser.add_argument(
        '--entrypoint',
        type=str,
        default=None,
        help='The entrypoint is the basic gunicorn command. By default, it\'s taken from app.yaml. '
             'This parameter can be used to set a different entrypoint. '
             'To provide this parameter via ViUR-CLI, you have to double quote it: '
             ' --entrypoint "\'gunicorn -b :$PORT --disable-redirect-access-to-syslog main:app\'"'
    )
    argument_parser.add_argument(
        '--port',
        type=int,
        default=8080,
        help='port to which we bind the application'
    )
    argument_parser.add_argument(
        '--gunicorn_port',
        type=int,
        default=8090,
        help='internal gunicorn port'
    )
    argument_parser.add_argument(
        '--workers', '--worker',
        type=int,
        default=1,
        help='amount of gunicorn workers'
    )
    argument_parser.add_argument(
        '--threads',
        type=int,
        default=5,
        help='amount of gunicorn threads'
    )
    argument_parser.add_argument(
        '--timeout',
        type=int,
        default=60,
        help='Time is seconds before gunicorn abort a request'
    )
    argument_parser.add_argument(
        '-V', '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )

    argument_parser.add_argument(
        '--env_var', metavar="KEY=VALUE", nargs="*",
        help="Set environment variable for the runtime. Each env_var is in "
             "the format of KEY=VALUE, and you can define multiple "
             "environment variables. You can also define them in app.yaml."
    )

    args = argument_parser.parse_args()

    app_folder = Path(args.distribution_folder)

    # load & parse the app.yaml
    with open(app_folder / args.appyaml, "r") as f:
        app_yaml = yaml.load(f, Loader=yaml.Loader)

    utils.set_env_vars(args.app_id, args, app_yaml)
    utils.patch_gunicorn()
    # Check for correct runtime
    current_runtime = f"python{sys.version_info.major}{sys.version_info.minor}"
    app_runtime = app_yaml["runtime"]
    assert app_runtime == current_runtime, f"app.yaml specifies {app_runtime} but you're on {current_runtime}, please correct this."

    if os.environ.get("WERKZEUG_RUN_MAIN"):
        # only start subprocesses wenn reloader starts
        start_gunicorn(args, app_yaml, app_folder)

    start_server(args.host, args.port, args.gunicorn_port, app_folder, app_yaml,
                 args.timeout)

    try:
        for process in subprocesses:
            process.kill()
    except:
        pass


if __name__ == '__main__':
    main()
