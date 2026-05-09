import logging
import logging.config
import os
import socket
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional, Union

import click

from android_runner.device import DeviceKind
from android_runner.emulator import AndroidEmulator
from android_runner.genymotion_saas import GenymotionSaas
from android_runner.genymotion_aws import GenymotionAws
from android_runner.process import ProcessRunner, ServiceKind
from android_runner.utils import str_to_bool, require_env
from android_runner import env_vars


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("CLI")


def get_device_instance(device_type: str) -> Optional[Union[AndroidEmulator, GenymotionSaas, GenymotionAws]]:
    """Create and return a device instance based on the device type."""
    device_type_lower = device_type.lower()

    if device_type_lower == DeviceKind.EMULATOR.value:
        emu_version = require_env(env_vars.EMU_ANDROID_VERSION)
        emu_img_type = require_env(env_vars.EMU_IMAGE_TYPE)
        emu_sys_img = require_env(env_vars.EMU_SYSTEM_IMAGE)

        emu_device = os.getenv(env_vars.EMU_DEVICE, "Nexus 5")
        emu_partition = os.getenv(env_vars.EMU_DATA_PARTITION, "550m")
        emu_args = os.getenv(env_vars.EMU_ARGS, "")
        emu_name = os.getenv(
            env_vars.EMU_NAME,
            f"{emu_device.replace(' ', '_').lower()}_{emu_version}",
        )

        return AndroidEmulator(
            emu_name, emu_device, emu_version, emu_partition,
            emu_args, emu_img_type, emu_sys_img
        )
    elif device_type_lower == DeviceKind.GENY_SAAS.value:
        return GenymotionSaas()
    elif device_type_lower == DeviceKind.GENY_AWS.value:
        return GenymotionAws()
    else:
        return None


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def main():
    """Android Runner CLI - manage Android emulators and cloud devices."""
    pass


def run_appium() -> None:
    """Start Appium server if enabled."""
    if str_to_bool(os.getenv(env_vars.APPIUM)):
        appium_runner = ProcessRunner(
            "Appium",
            "/usr/local/bin/appium",
            os.getenv(env_vars.APPIUM_ARGS, ""),
            use_terminal=False,
        )
        appium_runner.start()
    else:
        logger.info("APPIUM not enabled, skipping")


def run_device() -> None:
    """Start the configured device."""
    device_type = require_env(env_vars.DEVICE_TYPE)
    device = get_device_instance(device_type)

    if device is None:
        raise RuntimeError(f"'{device_type}' is not a valid device type!")

    device.create()
    device.start()
    device.wait_until_ready()
    device.reconfigure()
    device.keep_running()


def run_display_screen() -> None:
    """Start Xvfb display server."""
    display = os.getenv(env_vars.DISPLAY)
    screen_num = os.getenv(env_vars.SCREEN_NUMBER)
    width = os.getenv(env_vars.SCREEN_WIDTH)
    height = os.getenv(env_vars.SCREEN_HEIGHT)
    depth = os.getenv(env_vars.SCREEN_DEPTH)

    args = f"{display} -screen {screen_num} {width}x{height}x{depth}"
    runner = ProcessRunner("display", "/usr/bin/Xvfb", args, use_terminal=False)
    runner.start()


def run_display_wm() -> None:
    """Start openbox window manager."""
    runner = ProcessRunner("wm", "/usr/bin/openbox-session")
    runner.start()


def run_port_forwarder() -> None:
    """Set up port forwarding for emulator access."""
    local_ip = socket.gethostbyname(socket.gethostname())
    cmd = (
        f"/usr/bin/socat tcp-listen:5554,bind={local_ip},fork tcp:127.0.0.1:5554 & "
        f"/usr/bin/socat tcp-listen:5555,bind={local_ip},fork tcp:127.0.0.1:5555"
    )
    runner = ProcessRunner("port_fwd", cmd)
    runner.start()


def run_vnc_server() -> None:
    """Start VNC server."""
    vnc_pass = os.getenv(env_vars.VNC_PASSWORD)

    if vnc_pass:
        work_path = os.getenv(env_vars.WORK_PATH, "/tmp")
        pass_file = os.path.join(work_path, ".vncpass")
        subprocess.check_call(f"/usr/bin/x11vnc -storepasswd {vnc_pass} {pass_file}", shell=True)
        auth_arg = f"-rfbauth {pass_file}"
    else:
        auth_arg = "-nopw"

    display = os.getenv(env_vars.DISPLAY)
    args = f"-display {display} -forever -shared {auth_arg}"
    runner = ProcessRunner("vnc", "/usr/bin/x11vnc", args, use_terminal=False)
    runner.start()


def run_vnc_web() -> None:
    """Start noVNC web proxy if enabled."""
    if str_to_bool(os.getenv(env_vars.WEB_VNC)):
        vnc_port = require_env(env_vars.VNC_PORT)
        web_port = require_env(env_vars.WEB_VNC_PORT)
        args = f"--vnc localhost:{vnc_port} localhost:{web_port}"
        runner = ProcessRunner("vnc_web", "/opt/noVNC/utils/novnc_proxy", args, use_terminal=False)
        runner.start()
    else:
        logger.info("WEB_VNC not enabled, skipping")


@main.command()
@click.argument("service", type=click.Choice([s.value for s in ServiceKind]))
def start(service):
    """Start a service (appium, device, display_screen, display_wm, port_forwarder, vnc_server, vnc_web)."""
    service_lower = service.lower()

    handlers = {
        ServiceKind.APPIUM.value: run_appium,
        ServiceKind.DEVICE.value: run_device,
        ServiceKind.DISPLAY_SCREEN.value: run_display_screen,
        ServiceKind.DISPLAY_WM.value: run_display_wm,
        ServiceKind.PORT_FORWARDER.value: run_port_forwarder,
        ServiceKind.VNC_SERVER.value: run_vnc_server,
        ServiceKind.VNC_WEB.value: run_vnc_web,
    }

    handler = handlers.get(service_lower)
    if handler:
        handler()
    else:
        logger.error(f"Unknown service: {service}")


def run_log_server() -> None:
    """Start HTTP server for sharing logs."""
    if str_to_bool(os.getenv(env_vars.WEB_LOG)):
        log_path = require_env(env_vars.LOG_PATH)
        log_port = int(require_env(env_vars.WEB_LOG_PORT))
        logger.info(f"Log sharing enabled on port {log_port}")

        class LogHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/":
                    html = "<html><body>"
                    for filename in os.listdir(log_path):
                        html += f'<p><a href="{filename}">{filename}</a></p>'
                    html += "</body></html>"

                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(html.encode())
                else:
                    file_path = os.path.join(log_path, self.path.lstrip("/"))
                    try:
                        with open(file_path, "rb") as f:
                            self.send_response(200)
                            self.send_header("Content-type", "text/plain")
                            self.end_headers()
                            self.wfile.write(f.read())
                    except FileNotFoundError:
                        self.send_error(404, "File not found")

        server = HTTPServer(("0.0.0.0", log_port), LogHandler)
        server.serve_forever()
    else:
        logger.info("WEB_LOG not enabled, nothing to share")


@main.command()
@click.argument("component", type=click.Choice(["log"]))
def share(component):
    """Share a component (log)."""
    if component.lower() == "log":
        run_log_server()
    else:
        logger.error(f"Unknown component: {component}")


if __name__ == "__main__":
    main()
