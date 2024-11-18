import argparse
import os
import time


def patch_gunicorn():
    import gunicorn.workers.base
    with open(gunicorn.workers.base.__file__, 'r+') as file:
        content = file.read()

        if "except (SyntaxError, NameError) as e:" in content:
            return 0

        file.seek(0)
        file.write(content.replace(
            '        except SyntaxError as e:',
            '        except (SyntaxError, NameError) as e:'
        ))


def set_env_vars(application_id: str, args: argparse.Namespace, app_yaml: dict):
    """set necessary environment variables"""
    # First, merge the app.yaml into the environment so that the variables
    # from the CLI can overwrite it.
    if env_vars := app_yaml.get("env_variables"):
        if not isinstance(env_vars, dict):
            raise TypeError(
                f"env_variables section in app.yaml must be a dict. Got {type(env_vars)}")
        os.environ |= {k: str(v) for k, v in app_yaml["env_variables"].items()}

    os.environ["GAE_ENV"] = "localdev"
    os.environ["CLOUDSDK_CORE_PROJECT"] = application_id
    os.environ["GOOGLE_CLOUD_PROJECT"] = application_id
    os.environ["GAE_VERSION"] = str(time.time())
    os.environ["GRPC_ENABLE_FORK_SUPPORT"] = "0"

    # Merge environment variables from CLI parameter
    if args.env_var:
        os.environ |= dict(v.split("=", 1) for v in args.env_var)
