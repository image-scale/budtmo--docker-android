import logging
import subprocess
from enum import Enum


class ServiceKind(Enum):
    """Supported application/service types."""

    APPIUM = "appium"
    DEVICE = "device"
    DISPLAY_SCREEN = "display_screen"
    DISPLAY_WM = "display_wm"
    PORT_FORWARDER = "port_forwarder"
    VNC_SERVER = "vnc_server"
    VNC_WEB = "vnc_web"


class ProcessRunner:
    """Manages starting external processes with optional terminal UI."""

    def __init__(
        self,
        name: str,
        command: str,
        extra_args: str = "",
        use_terminal: bool = False,
    ) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.name = name
        self.command = command
        self.extra_args = extra_args
        self.use_terminal = use_terminal

    def start(self) -> None:
        """Start the process."""
        full_cmd = f"{self.command} {self.extra_args}".strip()

        if self.use_terminal:
            self.logger.info(f"{self.name} starting with terminal UI")
            wrapped = f"/usr/bin/xterm -T {self.name} -n {self.name} -e '{full_cmd}'"
            subprocess.check_call(wrapped, shell=True)
        else:
            self.logger.info(f"{self.name} starting in background")
            subprocess.check_call(full_cmd, shell=True)

    def __repr__(self) -> str:
        return (
            f"ProcessRunner(name={self.name}, command={self.command}, "
            f"args={self.extra_args}, terminal={self.use_terminal})"
        )
