import logging
import os
import signal
import time
from abc import ABC, abstractmethod
from enum import Enum

from android_runner.utils import str_to_bool
from android_runner import env_vars, status


class DeviceKind(Enum):
    EMULATOR = "emulator"
    GENY_SAAS = "geny_saas"
    GENY_AWS = "geny_aws"


class BaseDevice(ABC):
    """Base class for all device types."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.kind: str = ""
        self.poll_interval = int(os.getenv(env_vars.DEVICE_POLL_INTERVAL, "2"))
        self.analytics_enabled = str_to_bool(os.getenv(env_vars.ANALYTICS_ENABLED, "true"))
        signal.signal(signal.SIGTERM, self.cleanup)

    def write_status(self, current_status: str) -> None:
        """Write device status to a file for external monitoring."""
        status_file = os.path.join(os.getenv(env_vars.WORK_PATH, "/tmp"), "device_status")
        with open(status_file, "w+") as f:
            f.write(current_status)

    def create(self) -> None:
        """Create the device."""
        self.write_status(status.CREATING)

    def start(self) -> None:
        """Start the device."""
        self.write_status(status.STARTING)

    def wait_until_ready(self) -> None:
        """Wait until the device is fully booted."""
        self.write_status(status.BOOTING)

    def reconfigure(self) -> None:
        """Apply runtime configuration to the device."""
        self.write_status(status.RECONFIGURING)

    def keep_running(self) -> None:
        """Keep the process alive to receive signals."""
        self.write_status(status.READY)
        self.logger.warning(f"{self.kind} process will be kept alive to handle signals...")
        while True:
            time.sleep(2)

    @abstractmethod
    def cleanup(self, *args) -> None:
        """Clean up resources on shutdown."""
        pass
