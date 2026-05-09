import logging
import os
import re
import subprocess
import time
from enum import Enum

from android_runner.device import BaseDevice, DeviceKind
from android_runner.utils import str_to_bool, require_env, create_symlink
from android_runner import env_vars, status


ENCODING = "utf-8"


class AndroidEmulator(BaseDevice):
    """Android emulator device manager."""

    SUPPORTED_DEVICES = (
        "Nexus 4",
        "Nexus 5",
        "Nexus 7",
        "Nexus One",
        "Nexus S",
        "Samsung Galaxy S6",
        "Samsung Galaxy S7",
        "Samsung Galaxy S7 Edge",
        "Samsung Galaxy S8",
        "Samsung Galaxy S9",
        "Samsung Galaxy S10",
        "Pixel C",
    )

    VERSION_TO_API = {
        "9.0": "28",
        "10.0": "29",
        "11.0": "30",
        "12.0": "32",
        "13.0": "33",
        "14.0": "34",
    }

    _next_port = 5554

    class BootState(Enum):
        BOOTED = "booted"
        RUNNING = "in running state"
        HOME_SCREEN = "at home screen"
        POPUP = "popup window"

    def __init__(
        self,
        name: str,
        device: str,
        android_version: str,
        data_partition: str,
        extra_args: str,
        image_type: str,
        system_image: str,
    ) -> None:
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.kind = DeviceKind.EMULATOR.value
        self.name = name

        if device not in self.SUPPORTED_DEVICES:
            raise RuntimeError(f"device '{device}' is not supported!")
        self.device = device

        if android_version not in self.VERSION_TO_API:
            raise RuntimeError(f"android version '{android_version}' is not supported!")
        self.android_version = android_version
        self.api_level = self.VERSION_TO_API[android_version]

        self.adb_name = f"emulator-{AndroidEmulator._next_port}"
        AndroidEmulator._next_port += 2

        self.data_partition = data_partition
        self.extra_args = extra_args
        self.image_type = image_type
        self.system_image = system_image

        workdir = require_env(env_vars.WORK_PATH)
        self.profile_target = os.path.join(workdir, ".android", "devices.xml")
        self.emu_path = os.path.join(workdir, "emulator")
        self.config_path = os.path.join(workdir, "emulator", "config.ini")
        self.profiles_dir = os.path.join(workdir, "docker-android", "mixins", "configs", "devices", "profiles")
        self.skins_dir = os.path.join(workdir, "docker-android", "mixins", "configs", "devices", "skins")

        self.file_name = self.device.replace(" ", "_").lower()
        self.skip_skin = str_to_bool(os.getenv(env_vars.EMU_NO_SKIN))
        self.boot_wait_time = 15

    def is_initialized(self) -> bool:
        """Check if the emulator has been created with the current device configuration."""
        if not os.path.exists(self.config_path):
            self.logger.info("Config file does not exist")
            return False

        self.logger.info("Config file exists")
        with open(self.config_path, "r") as f:
            for line in f:
                if re.match(rf"hw\.device\.name ?= ?{self.device}", line):
                    self.logger.info("Selected device is already created")
                    return True

        self.logger.info("Selected device is not created")
        return False

    def _link_device_profile(self) -> None:
        """Link Samsung device profile if needed."""
        if "samsung" in self.device.lower():
            profile_source = os.path.join(self.profiles_dir, f"{self.file_name}.xml")
            create_symlink(profile_source, self.profile_target)
            self.logger.info("Samsung device profile is linked")

    def _apply_override_config(self) -> None:
        """Apply override configuration if specified."""
        override_path = os.getenv(env_vars.EMU_OVERRIDE_CONFIG)

        if override_path is None:
            self.logger.info("Override config path not set")
            return

        self.logger.info(f"Override config path found: {override_path}")

        if not os.path.isfile(override_path):
            self.logger.warning(f"Override file '{override_path}' does not exist")
            return

        if not os.access(override_path, os.R_OK):
            self.logger.warning(f"Override file '{override_path}' is not readable")
            return

        try:
            with open(override_path, "r") as src, open(self.config_path, "a") as dst:
                dst.write(src.read())
            self.logger.info(f"Applied override config from '{override_path}'")
        except Exception as e:
            self.logger.error(f"Failed to apply override config: {e}")

    def _write_skin_config(self) -> None:
        """Write skin and additional configuration."""
        skin_path = os.path.join(self.skins_dir, self.file_name)
        with open(self.config_path, "a") as f:
            f.write("hw.keyboard=yes\n")
            f.write(f"disk.dataPartition.size={self.data_partition}\n")
            f.write(f"skin.path={'_no_skin' if self.skip_skin else skin_path}\n")
        self.logger.info(f"Skin config written to: '{self.config_path}'")

    def create(self) -> None:
        """Create the emulator AVD."""
        super().create()
        first_run = not self.is_initialized()
        if first_run:
            self.logger.info(f"Creating the {self.kind}...")
            self._link_device_profile()

            escaped_device = self.device.replace(" ", r"\ ")
            cmd = (
                f"avdmanager create avd -f -n {self.name} "
                f"-b {self.image_type}/{self.system_image} "
                f"-k 'system-images;android-{self.api_level};{self.image_type};{self.system_image}' "
                f"-d {escaped_device} -p {self.emu_path}"
            )
            self.logger.info(f"Creation command: '{cmd}'")
            subprocess.check_call(cmd, shell=True)

            self._write_skin_config()
            self._apply_override_config()
            self.logger.info(f"{self.kind} is created!")

    def _set_kvm_permissions(self) -> None:
        """Grant KVM permissions for hardware acceleration."""
        kvm_path = "/dev/kvm"
        if os.path.exists(kvm_path):
            cmds = (
                f"sudo chown 1300:1301 {kvm_path}",
                "sudo sed -i '1d' /etc/passwd",
            )
            for c in cmds:
                subprocess.check_call(c, shell=True)
            self.logger.info("KVM permission granted")
        else:
            raise RuntimeError("/dev/kvm not found")

    def _launch(self) -> None:
        """Launch the emulator process."""
        self.logger.info(f"Launching the {self.kind}")
        base_args = "-gpu swiftshader_indirect -accel on -writable-system -verbose"
        wipe_arg = "-wipe-data" if not self.is_initialized() else ""
        cmd = f"emulator @{self.name} {base_args} {wipe_arg} {self.extra_args}"
        self.logger.info(f"Launch command: '{cmd}'")
        subprocess.Popen(cmd.split())

    def start(self) -> None:
        """Start the emulator."""
        super().start()
        self._set_kvm_permissions()
        self._launch()

    def run_adb_check(
        self,
        check_type: BootState,
        command: str,
        expected: str,
        max_tries: int,
        wait_time: int,
        action_cmd: str = None,
    ) -> None:
        """Run an ADB command check in a loop until success or exhaustion."""
        success = False
        attempt = 0

        for attempt in range(1, max_tries + 1):
            if success:
                break
            try:
                output = subprocess.check_output(command.split()).decode(ENCODING)
                if expected.lower() in output.lower():
                    if check_type is self.BootState.POPUP:
                        subprocess.check_call(action_cmd, shell=True)
                    else:
                        self.logger.info(f"{self.kind} is {check_type.value}!")
                        success = True
                else:
                    self.logger.info(
                        f"[attempt: {attempt}] {self.kind} not {check_type.value}! "
                        f"Retrying in {wait_time}s"
                    )
                    time.sleep(wait_time)
            except subprocess.CalledProcessError:
                self.logger.warning("ADB command failed, retrying...")
                time.sleep(2)
                continue

        if not success:
            if check_type is self.BootState.POPUP:
                self.logger.info(f"Popup '{expected}' not found")
            else:
                raise RuntimeError(f"{check_type.value} checked {attempt} times without success")

    def wait_until_ready(self) -> None:
        """Wait until the emulator is fully booted and ready."""
        super().wait_until_ready()

        boot_cmd = f"adb -s {self.adb_name} wait-for-device shell getprop sys.boot_completed"
        focus_cmd = f"adb -s {self.adb_name} shell dumpsys window | grep -i mCurrentFocus"

        self.run_adb_check(self.BootState.BOOTED, boot_cmd, "1", 60, self.poll_interval)
        time.sleep(self.boot_wait_time)

        popup_attempts = 3
        popup_wait = 0

        system_ui_popup = "Not Responding: com.android.systemui"
        system_ui_fix = f"adb shell su root 'kill $(pidof com.android.systemui)'"
        self.run_adb_check(
            self.BootState.POPUP, focus_cmd, system_ui_popup, popup_attempts, popup_wait, system_ui_fix
        )

        enter_popups = [
            "Not Responding: com.google.android.gms",
            "Not Responding: system",
            "ConversationListActivity",
        ]
        enter_cmd = "adb shell input keyevent KEYCODE_ENTER"
        for popup in enter_popups:
            self.run_adb_check(
                self.BootState.POPUP, focus_cmd, popup, popup_attempts, popup_wait, enter_cmd
            )

        self.run_adb_check(
            self.BootState.HOME_SCREEN, focus_cmd, "launcheractivity", 60, self.poll_interval
        )
        self.logger.info(f"{self.kind} is ready to use")

    def cleanup(self, *args) -> None:
        """Handle cleanup on SIGTERM."""
        self.logger.warning("SIGTERM received - nothing to clean up for emulator")

    def __repr__(self) -> str:
        return (
            f"AndroidEmulator(name={self.name}, device={self.device}, "
            f"adb_name={self.adb_name}, android_version={self.android_version})"
        )
