import tempfile
import arrow
import shutil
import requests
import time
import threading
import sys
import click
from consts import ODOO_USER
import subprocess
import configparser
import os
from wodoo import odoo_config
from wodoo.odoo_config import customs_dir
from wodoo.odoo_config import get_conn_autoclose
from wodoo.odoo_config import current_version
from pathlib import Path

pidfile = Path("/tmp/odoo.pid")
config = odoo_config.get_settings()
version = odoo_config.current_version()

is_odoo_cronjob = os.getenv("IS_ODOO_CRONJOB", "0") == "1"
is_odoo_queuejob = os.getenv("IS_ODOO_QUEUEJOB", "0") == "1"


def _replace_params_in_config(ADDONS_PATHS, content, server_wide_modules=None):
    if not config.get("DB_HOST", "") or not config.get("DB_USER", ""):
        raise Exception("Please define all DB Env Variables!")
    content = content.replace("__ADDONS_PATH__", ADDONS_PATHS)
    content = content.replace(
        "__ENABLE_DB_MANAGER__",
        "True" if config["ODOO_ENABLE_DB_MANAGER"] == "1" else "False",
    )
    content = content.replace(
        "__LIMIT_MEMORY_HARD__", config.get("LIMIT_MEMORY_HARD", "32000000000")
    )
    content = content.replace(
        "__LIMIT_MEMORY_SOFT__", config.get("LIMIT_MEMORY_SOFT", "31000000000")
    )

    server_wide_modules = ",".join(_get_server_wide_modules(server_wide_modules))
    content = content.replace("__SERVER_WIDE_MODULES__", server_wide_modules)

    for key, value in os.environ.items():
        key = f"__{key}__"
        content = content.replace(key, value)

    for key in config.keys():
        content = content.replace("__{}__".format(key), config[key])
    for key in os.environ.keys():
        content = content.replace("__{}__".format(key), os.getenv(key, ""))

    # exchange existing configurations
    return content


def _run_autosetup():
    path = customs_dir() / "autosetup"
    if path.exists():
        for file in path.glob("*.sh"):
            print("executing {}".format(file))
            os.chdir(path.parent)
            subprocess.check_call(
                [
                    file,
                    os.environ["ODOO_AUTOSETUP_PARAM"],
                ]
            )


def _replace_variables_in_config_files(local_config):
    config_dir = Path(os.environ["ODOO_CONFIG_DIR"])
    config_dir_template = Path(os.environ["ODOO_CONFIG_TEMPLATE_DIR"])
    config_dir.mkdir(exist_ok=True, parents=True)
    for file in config_dir_template.glob("*"):
        path = str(config_dir / file.name)
        shutil.copy(str(file), path)
        subprocess.call(["chmod", "a+r", path])
        del path

    no_extra_addons_paths = False
    if local_config and local_config.no_extra_addons_paths:
        no_extra_addons_paths = True
    additional_addons_paths = False
    if local_config and local_config.additional_addons_paths:
        additional_addons_paths = local_config.additional_addons_paths

    ADDONS_PATHS = ",".join(
        list(
            map(
                str,
                odoo_config.get_odoo_addons_paths(
                    no_extra_addons_paths=no_extra_addons_paths,
                    additional_addons_paths=(additional_addons_paths or "").split(","),
                ),
            )
        )
    )

    config_dir = Path(os.getenv("ODOO_CONFIG_DIR"))

    def _get_config(filepath):
        content = filepath.read_text()
        server_wide_modules = None
        if local_config and local_config.server_wide_modules:
            server_wide_modules = local_config.server_wide_modules.split(",") or None
        elif os.getenv("SERVER_WIDE_MODULES"):
            server_wide_modules = os.environ["SERVER_WIDE_MODULES"].split(",")

        content = _replace_params_in_config(
            ADDONS_PATHS, content, server_wide_modules=server_wide_modules
        )
        cfg = configparser.ConfigParser()
        cfg.read_string(content)
        return cfg

    common_config = _get_config(config_dir / "common")
    for file in config_dir.glob("config_*"):
        config_file_content = _get_config(file)
        for section in common_config.sections():
            for k, v in common_config[section].items():
                if (
                    section not in config_file_content.sections()
                    or k not in config_file_content[section]
                ):
                    config_file_content[section][k] = v
        if config["ODOO_ADMIN_PASSWORD"]:
            config_file_content["options"]["admin_passwd"] = config[
                "ODOO_ADMIN_PASSWORD"
            ]

        if "without_demo" not in config_file_content["options"]:
            if os.getenv("ODOO_DEMO", "") == "1":
                config_file_content["options"]["without_demo"] = "False"
            else:
                config_file_content["options"]["without_demo"] = "all"

        with open(file, "w") as configfile:
            config_file_content.write(configfile)


def _run_libreoffice_in_background():
    subprocess.Popen(["/bin/bash", os.environ["ODOOLIB"] + "/run_soffice.sh"])


def get_config_file(confname):
    return str(Path(os.environ["ODOO_CONFIG_DIR"]) / confname)


def prepare_run(local_config=None):

    _replace_variables_in_config_files(local_config)

    if config["RUN_AUTOSETUP"] == "1":
        _run_autosetup()

    _run_libreoffice_in_background()

    # make sure out dir is owned by odoo user to be writable
    user_id = int(os.getenv("OWNER_UID", os.getuid()))
    for path in [
        os.environ["OUT_DIR"],
        os.environ["RUN_DIR"],
        os.environ["ODOO_DATA_DIR"],
        os.getenv("INTERCOM_DIR", ""),
        Path(os.environ["RUN_DIR"]) / "debug",
        Path(os.environ["ODOO_DATA_DIR"]) / "addons",
        Path(os.environ["ODOO_DATA_DIR"]) / "filestore",
        Path(os.environ["ODOO_DATA_DIR"]) / "sessions",
    ]:
        if not path:
            continue
        out_dir = Path(path)
        if not out_dir.exists() and not out_dir.is_symlink():
            out_dir.mkdir(parents=True, exist_ok=True)
        if out_dir.exists():
            if out_dir.stat().st_uid == 0:
                shutil.chown(str(out_dir), user=user_id, group=user_id)
        del path
        del out_dir

    if os.getenv("IS_ODOO_QUEUEJOB", "") == "1":
        # https://www.odoo.com/apps/modules/10.0/queue_job/
        sql = "update queue_job set state='pending' where state in ('started', 'enqueued');"
        with get_conn_autoclose() as cr:
            cr.execute(sql)


def get_odoo_bin(for_shell=False):
    if is_odoo_cronjob and not config.get("RUN_ODOO_CRONJOBS") == "1":
        print("Cronjobs shall not run. Good-bye!")
        sys.exit(0)

    if is_odoo_queuejob and not config.get("RUN_ODOO_QUEUEJOBS") == "1":
        print("Queue-Jobs shall not run. Good-bye!")
        sys.exit(0)

    EXEC = "odoo-bin"
    if is_odoo_cronjob:
        print("Starting odoo cronjobs")
        CONFIG = "config_cronjob"
        if version <= 9.0:
            EXEC = "openerp-server"

    elif is_odoo_queuejob:
        print("Starting odoo queuejobs")
        CONFIG = "config_queuejob"

    else:
        CONFIG = "config_webserver"
        if version <= 9.0:
            if for_shell:
                EXEC = "openerp-server"
            else:
                EXEC = "openerp-server"
        else:
            try:
                if config.get("ODOO_GEVENT_MODE", "") == "1":
                    raise Exception("Dont use GEVENT MODE anymore")
            except KeyError:
                pass
            if os.getenv("ODOO_QUEUEJOBS_CRON_IN_ONE_CONTAINER", "") == "1":
                CONFIG = "config_allinone"

            if os.getenv("ODOO_CRON_IN_ONE_CONTAINER", "") == "1":
                CONFIG = "config_web_and_cron"

    EXEC = "{}/{}".format(os.environ["SERVER_DIR"], EXEC)
    return EXEC, CONFIG


def kill_odoo():
    if pidfile.exists():
        print("Killing Odoo")
        pid = pidfile.read_text()
        cmd = ["/bin/kill", "-9", pid]
        if (
            os.getenv("USE_DOCKER", "") == "1"
            and os.getenv("DOCKER_MACHINE", "") == "1"
        ):
            cmd = [
                "/usr/bin/sudo",
            ] + cmd
        subprocess.call(cmd)
        try:
            pidfile.unlink()
        except FileNotFoundError:
            pass
    else:
        if version <= 9.0:
            subprocess.call(
                [
                    "/usr/bin/sudo",
                    "/usr/bin/pkill",
                    "-9",
                    "-f",
                    "openerp-server",
                ]
            )
            subprocess.call(
                [
                    "/usr/bin/sudo",
                    "/usr/bin/pkill",
                    "-9",
                    "-f",
                    "openerp-gevent",
                ]
            )
        else:
            subprocess.call(
                [
                    "/usr/bin/sudo",
                    "/usr/bin/pkill",
                    "-9",
                    "-f",
                    "odoo-bin",
                ]
            )


def __python_exe(remote_debug=False, wait_for_remote=False):
    if version <= 10.0:
        cmd = ["/usr/bin/python"]
    else:
        # return "/usr/bin/python3"
        cmd = ["/opt/venv/bin/python3"]

    if remote_debug or wait_for_remote:
        cmd += [
            "-mdebugpy",
            "--listen",
            "0.0.0.0:5678",
        ]

    if wait_for_remote:
        cmd += [
            "--wait-for-client",
        ]
    return cmd


def wait_postgres(timeout=10):
    import psycopg2

    def connect():
        psycopg2.connect(
            dbname="postgres",
            host=os.environ["DB_HOST"],
            user=os.environ["DB_USER"],
            password=os.environ["DB_PWD"],
        )

    deadline = arrow.get().shift(seconds=timeout)
    count = 0
    sleep = 0.5
    while arrow.get() < deadline:
        count += 1
        try:
            connect()
        except Exception as ex:
            click.secho("Waiting for postgres to arrive", fg='blue')
            time.sleep(sleep)
            if count > 3:
                click.secho(ex, fg='red')
            sleep *= 1.4
        else:
            break


def exec_odoo(
    CONFIG,
    *args,
    odoo_shell=False,
    touch_url=False,
    on_done=None,
    stdin=None,
    dokill=True,
    remote_debug=False,
    wait_for_remote=False,
    **kwargs,
):  # NOQA
    assert not [x for x in args if "--pidfile" in x], "Not custom pidfile allowed"

    if dokill:
        kill_odoo()

    wait_postgres()

    EXEC, _CONFIG = get_odoo_bin(for_shell=odoo_shell)
    CONFIG = get_config_file(CONFIG or _CONFIG)
    cmd = []
    if os.getenv("ODOO_SUDO_CMD") == "1":
        cmd = [
            "/usr/bin/sudo",
            "-E",
            "-H",
            "-u",
            ODOO_USER,
        ]
    cmd += __python_exe(remote_debug=remote_debug, wait_for_remote=wait_for_remote) + [
        EXEC,
    ]
    if odoo_shell:
        cmd += ["shell"]
    try:
        DBNAME = config["DBNAME"]
    except KeyError:
        DBNAME = os.environ["DBNAME"]
    cmd += ["-c", CONFIG, "-d", DBNAME]

    print(Path(CONFIG).read_text())
    if not odoo_shell:
        cmd += [
            f"--pidfile={pidfile}",
        ]
    cmd += args

    cmd = " ".join(map(lambda x: f'"{x}"', cmd))

    if touch_url:
        _touch()

    filename = Path(tempfile.mktemp(suffix=".exitcode"))
    cmd += f" || echo $? > {filename}"

    # if stdin:
    #     cmd = f'{stdin} |' + cmd
    if stdin:
        if isinstance(stdin, str):
            stdin = stdin.encode("utf-8")
        subprocess.run(cmd, input=stdin, shell=True)
    else:
        subprocess.run(cmd, shell=True)
    print(cmd)
    if pidfile.exists():
        pidfile.unlink()
    if on_done:
        on_done()

    rc = 0
    if filename.exists():
        try:
            rc = int(filename.read_text().strip())
        except ValueError:
            rc = -1  # undefined return code
        finally:
            filename.unlink()
    return rc


def _run_shell_cmd(code, do_raise=False):
    cmd = [
        "--stop-after-init",
    ]
    if current_version() >= 11.0:
        cmd += ["--shell-interface=ipython"]

    rc = exec_odoo(
        "config_shell",
        *cmd,
        odoo_shell=True,
        stdin=code,
        dokill=False,
    )
    if do_raise and rc:
        click.secho(("Failed at: \n" f"{code}",), fg="red")
        sys.exit(-1)
    return rc


def _get_server_wide_modules(server_wide_modules=None):
    if not server_wide_modules:
        server_wide_modules = (os.getenv("SERVER_WIDE_MODULES", "") or "").split(",")

    if (
        os.getenv("IS_ODOO_QUEUEJOB", "") == "1"
        or os.getenv("ODOO_QUEUEJOBS_CRON_IN_ONE_CONTAINER", "") == "1"
    ):
        if "queue_job" not in server_wide_modules:
            server_wide_modules.append("queue_job")

    if (
        os.getenv("IS_ODOO_QUEUEJOB", "") != "1"
        and os.getenv("ODOO_QUEUEJOBS_CRON_IN_ONE_CONTAINER", "") != "1"
    ):
        if "queue_job" in server_wide_modules:
            server_wide_modules.remove("queue_job")

    if (
        os.getenv("ODOO_CRON_IN_WEB_CONTAINER", "") == "1"
        and os.getenv("ODOO_QUEUEJOBS_CRON_IN_ONE_CONTAINER", "") != "1"
    ):
        if "queue_job" in server_wide_modules:
            server_wide_modules.remove("queue_job")
    return server_wide_modules

def _touch():
    def toucher():
        while True:
            try:
                r = requests.get(
                    "http://localhost:{}".format(os.environ["INTERNAL_ODOO_PORT"])
                )
                r.raise_for_status()
                print("HTTP Get to odoo succeeded.")
                break
            finally:
                time.sleep(2)

    t = threading.Thread(target=toucher)
    t.daemon = True
    print("Touching odoo url to start it")
    t.start()