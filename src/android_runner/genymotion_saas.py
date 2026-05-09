import concurrent.futures
import json
import logging
import os
import subprocess
import uuid

from android_runner.device import BaseDevice, DeviceKind
from android_runner.utils import require_env
from android_runner import env_vars


ENCODING = "utf-8"


class GenymotionBase(BaseDevice):
    """Base class for Genymotion cloud devices."""

    def __init__(self) -> None:
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def load_template(self, filename: str) -> list:
        """Load device configuration from a JSON template file."""
        template_dir = require_env(env_vars.GENY_TEMPLATE_PATH)
        template_path = os.path.join(template_dir, filename)

        if not os.path.isfile(template_path):
            self._shutdown_and_logout()
            raise RuntimeError(f"'{template_path}' cannot be found!")

        try:
            self.logger.info(f"Loading template: {template_path}")
            with open(template_path, "r") as f:
                return json.load(f)
        except FileNotFoundError as e:
            self._shutdown_and_logout()
            self.logger.error(f"File not found: {e}")
            raise
        except json.JSONDecodeError as e:
            self._shutdown_and_logout()
            self.logger.error(f"Invalid JSON: {e}")
            raise

    def _login(self) -> None:
        """Authenticate with the Genymotion service."""
        raise NotImplementedError

    def _shutdown_and_logout(self) -> None:
        """Stop all devices and logout."""
        raise NotImplementedError

    def create(self) -> None:
        super().create()
        self._login()

    def cleanup(self, *args) -> None:
        self._shutdown_and_logout()


class GenymotionSaas(GenymotionBase):
    """Genymotion SaaS cloud device manager."""

    def __init__(self) -> None:
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.kind = DeviceKind.GENY_SAAS.value
        self.instances = []

    def _login(self) -> None:
        """Login using auth token or username/password."""
        if os.getenv(env_vars.GENY_AUTH_TOKEN):
            token = require_env(env_vars.GENY_AUTH_TOKEN)
            subprocess.check_call(f"gmsaas auth token {token} > /dev/null 2>&1", shell=True)
        else:
            user = require_env(env_vars.GENY_SAAS_USER)
            password = require_env(env_vars.GENY_SAAS_PASS)
            subprocess.check_call(f"gmsaas auth login {user} {password} > /dev/null 2>&1", shell=True)
        self.logger.info("Successfully logged in!")

    def _start_single_instance(self, config: dict) -> dict:
        """Create and connect a single Genymotion instance."""
        name = config.get("name") or str(uuid.uuid4())
        template = config.get("template")
        local_port = config.get("local_port")

        if not template:
            raise RuntimeError("'template' is a required parameter and not provided!")

        self.logger.info(f"Starting instance: name={name}, template={template}")

        cmd = f"gmsaas instances start {template} {name}"
        instance_id = subprocess.check_output(cmd.split()).decode(ENCODING).strip()

        connect_cmd = f"gmsaas instances adbconnect {instance_id}"
        if local_port:
            connect_cmd += f" --adb-serial-port {local_port}"

        subprocess.check_call(connect_cmd, shell=True)
        self.logger.info(f"Connected to instance: {instance_id}")

        return {name: instance_id}

    def _stop_single_instance(self, instance_info: dict) -> bool:
        """Stop a single instance."""
        for name, instance_id in instance_info.items():
            try:
                subprocess.check_call(f"gmsaas instances stop {instance_id}", shell=True)
                self.logger.info(f"Stopped instance '{name}'")
                return True
            except Exception as e:
                self.logger.error(f"Failed to stop '{name}': {e}")
                return False

    def create(self) -> None:
        """Create all instances from template."""
        super().create()

        configs = []
        for item in self.load_template(env_vars.GENY_SAAS_TEMPLATE):
            parsed = {}
            for key, value in item.items():
                key_lower = key.lower()
                if key_lower in ("name", "template", "local_port"):
                    parsed[key_lower] = value
                else:
                    self.logger.warning(f"Unknown config key '{key}', ignoring")
            configs.append(parsed)

        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            futures = {executor.submit(self._start_single_instance, cfg): cfg for cfg in configs}

            for future in concurrent.futures.as_completed(futures):
                cfg = futures[future]
                try:
                    result = future.result()
                    self.instances.append(result)
                    self.logger.info(f"Created instance: {result}")
                except Exception as e:
                    self.logger.error(f"Failed to create instance for {cfg.get('name', 'unknown')}: {e}")
                    self._shutdown_and_logout()
                    raise

    def _shutdown_and_logout(self) -> None:
        """Stop all instances and logout."""
        if self.instances:
            self.logger.info("Stopping all created instances...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
                futures = [executor.submit(self._stop_single_instance, inst) for inst in self.instances]
                for future in concurrent.futures.as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        self.logger.error(f"Error during shutdown: {e}")

        if os.getenv(env_vars.GENY_AUTH_TOKEN):
            subprocess.check_call("gmsaas auth reset", shell=True)
        else:
            subprocess.check_call("gmsaas auth logout", shell=True)
        self.logger.info("Successfully logged out!")
