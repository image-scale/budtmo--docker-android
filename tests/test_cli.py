import os
import tempfile
from unittest import TestCase, mock

from click.testing import CliRunner

from android_runner.cli import main, get_device_instance, run_appium, run_device
from android_runner.device import DeviceKind
from android_runner.emulator import AndroidEmulator
from android_runner.genymotion_saas import GenymotionSaas
from android_runner.genymotion_aws import GenymotionAws
from android_runner import env_vars


class TestCliBase(TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self.env_backup = {}
        self.temp_dir = tempfile.mkdtemp()
        self.default_envs = {
            env_vars.WORK_PATH: self.temp_dir,
            env_vars.ANALYTICS_ENABLED: "false",
            env_vars.EMU_NO_SKIN: "false",
        }
        for key, value in self.default_envs.items():
            self.env_backup[key] = os.environ.get(key)
            os.environ[key] = value

    def tearDown(self):
        for key, original in self.env_backup.items():
            if original is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original


class TestGetDeviceInstance(TestCliBase):
    def test_emulator_device(self):
        os.environ[env_vars.EMU_ANDROID_VERSION] = "11.0"
        os.environ[env_vars.EMU_IMAGE_TYPE] = "google_apis"
        os.environ[env_vars.EMU_SYSTEM_IMAGE] = "x86"
        os.environ[env_vars.EMU_DEVICE] = "Nexus 5"

        device = get_device_instance("emulator")

        self.assertIsInstance(device, AndroidEmulator)
        self.assertEqual(device.device, "Nexus 5")

        del os.environ[env_vars.EMU_ANDROID_VERSION]
        del os.environ[env_vars.EMU_IMAGE_TYPE]
        del os.environ[env_vars.EMU_SYSTEM_IMAGE]
        del os.environ[env_vars.EMU_DEVICE]

    def test_geny_saas_device(self):
        os.environ[env_vars.GENY_TEMPLATE_PATH] = self.temp_dir

        device = get_device_instance("geny_saas")

        self.assertIsInstance(device, GenymotionSaas)

        del os.environ[env_vars.GENY_TEMPLATE_PATH]

    def test_geny_aws_device(self):
        os.environ[env_vars.GENY_TEMPLATE_PATH] = self.temp_dir

        device = get_device_instance("geny_aws")

        self.assertIsInstance(device, GenymotionAws)

        del os.environ[env_vars.GENY_TEMPLATE_PATH]

    def test_invalid_device_type(self):
        device = get_device_instance("invalid_type")
        self.assertIsNone(device)


class TestStartCommand(TestCliBase):
    def test_start_appium_when_enabled(self):
        os.environ[env_vars.APPIUM] = "true"

        with mock.patch("android_runner.cli.ProcessRunner") as mock_runner:
            instance = mock_runner.return_value
            run_appium()
            instance.start.assert_called_once()

        del os.environ[env_vars.APPIUM]

    def test_start_appium_when_disabled(self):
        if env_vars.APPIUM in os.environ:
            del os.environ[env_vars.APPIUM]

        with mock.patch("android_runner.cli.ProcessRunner") as mock_runner:
            run_appium()
            mock_runner.assert_not_called()

    def test_start_device_invalid_type(self):
        os.environ[env_vars.DEVICE_TYPE] = "invalid_type"

        with self.assertRaises(RuntimeError) as ctx:
            run_device()

        self.assertIn("invalid_type", str(ctx.exception))

        del os.environ[env_vars.DEVICE_TYPE]


class TestCliCommands(TestCliBase):
    def test_help_option(self):
        result = self.runner.invoke(main, ["--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Android Runner CLI", result.output)

    def test_start_help(self):
        result = self.runner.invoke(main, ["start", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("appium", result.output)
        self.assertIn("device", result.output)

    def test_share_help(self):
        result = self.runner.invoke(main, ["share", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("log", result.output)

    def test_start_with_invalid_service(self):
        result = self.runner.invoke(main, ["start", "invalid"])
        self.assertNotEqual(result.exit_code, 0)


class TestVncServer(TestCliBase):
    def test_vnc_without_password(self):
        os.environ[env_vars.DISPLAY] = ":0"
        if env_vars.VNC_PASSWORD in os.environ:
            del os.environ[env_vars.VNC_PASSWORD]

        from android_runner.cli import run_vnc_server

        with mock.patch("android_runner.cli.ProcessRunner") as mock_runner:
            with mock.patch("subprocess.check_call"):
                instance = mock_runner.return_value
                run_vnc_server()
                mock_runner.assert_called_once()
                call_args = mock_runner.call_args[1] if mock_runner.call_args[1] else mock_runner.call_args[0]
                if isinstance(call_args, tuple):
                    self.assertIn("-nopw", str(call_args))

        del os.environ[env_vars.DISPLAY]


class TestVncWeb(TestCliBase):
    def test_vnc_web_when_disabled(self):
        if env_vars.WEB_VNC in os.environ:
            del os.environ[env_vars.WEB_VNC]

        from android_runner.cli import run_vnc_web

        with mock.patch("android_runner.cli.ProcessRunner") as mock_runner:
            run_vnc_web()
            mock_runner.assert_not_called()

    def test_vnc_web_when_enabled(self):
        os.environ[env_vars.WEB_VNC] = "true"
        os.environ[env_vars.VNC_PORT] = "5900"
        os.environ[env_vars.WEB_VNC_PORT] = "6080"

        from android_runner.cli import run_vnc_web

        with mock.patch("android_runner.cli.ProcessRunner") as mock_runner:
            instance = mock_runner.return_value
            run_vnc_web()
            mock_runner.assert_called_once()
            instance.start.assert_called_once()

        del os.environ[env_vars.WEB_VNC]
        del os.environ[env_vars.VNC_PORT]
        del os.environ[env_vars.WEB_VNC_PORT]
