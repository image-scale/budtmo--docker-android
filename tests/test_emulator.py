import os
import tempfile
from unittest import TestCase, mock

from android_runner.emulator import AndroidEmulator
from android_runner import env_vars


class TestEmulatorBase(TestCase):
    """Base test class that sets up required environment variables."""

    def setUp(self):
        self.env_backup = {}
        self.required_envs = {
            env_vars.WORK_PATH: "/home/testuser",
            env_vars.ANALYTICS_ENABLED: "false",
            env_vars.EMU_NO_SKIN: "false",
        }
        for key, value in self.required_envs.items():
            self.env_backup[key] = os.environ.get(key)
            os.environ[key] = value

    def tearDown(self):
        for key, original in self.env_backup.items():
            if original is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original


class TestEmulatorCreation(TestEmulatorBase):
    def test_create_with_supported_device(self):
        emu = AndroidEmulator(
            name="test_emu",
            device="Nexus 4",
            android_version="10.0",
            data_partition="550m",
            extra_args="",
            image_type="google_apis",
            system_image="x86",
        )
        self.assertEqual(emu.device, "Nexus 4")
        self.assertEqual(emu.name, "test_emu")

    def test_create_with_unsupported_device(self):
        with self.assertRaises(RuntimeError) as ctx:
            AndroidEmulator(
                name="test_emu",
                device="Unknown Device XYZ",
                android_version="10.0",
                data_partition="550m",
                extra_args="",
                image_type="google_apis",
                system_image="x86",
            )
        self.assertIn("not supported", str(ctx.exception))

    def test_case_sensitive_device_name(self):
        with self.assertRaises(RuntimeError):
            AndroidEmulator(
                name="test_emu",
                device="NEXUS 4",
                android_version="10.0",
                data_partition="550m",
                extra_args="",
                image_type="google_apis",
                system_image="x86",
            )


class TestEmulatorAndroidVersion(TestEmulatorBase):
    def test_supported_android_versions(self):
        versions = {
            "9.0": "28",
            "10.0": "29",
            "11.0": "30",
            "12.0": "32",
            "13.0": "33",
            "14.0": "34",
        }
        for version, expected_api in versions.items():
            emu = AndroidEmulator(
                name="test_emu",
                device="Nexus 5",
                android_version=version,
                data_partition="550m",
                extra_args="",
                image_type="google_apis",
                system_image="x86",
            )
            self.assertEqual(emu.api_level, expected_api)

    def test_unsupported_android_version(self):
        with self.assertRaises(RuntimeError) as ctx:
            AndroidEmulator(
                name="test_emu",
                device="Nexus 5",
                android_version="5.0",
                data_partition="550m",
                extra_args="",
                image_type="google_apis",
                system_image="x86",
            )
        self.assertIn("not supported", str(ctx.exception))


class TestEmulatorAdbName(TestEmulatorBase):
    def test_unique_adb_names(self):
        emu1 = AndroidEmulator(
            name="emu1",
            device="Nexus 4",
            android_version="10.0",
            data_partition="550m",
            extra_args="",
            image_type="google_apis",
            system_image="x86",
        )
        emu2 = AndroidEmulator(
            name="emu2",
            device="Nexus 5",
            android_version="11.0",
            data_partition="550m",
            extra_args="",
            image_type="google_apis",
            system_image="x86",
        )
        self.assertNotEqual(emu1.adb_name, emu2.adb_name)
        self.assertTrue(emu1.adb_name.startswith("emulator-"))
        self.assertTrue(emu2.adb_name.startswith("emulator-"))


class TestEmulatorInitialization(TestEmulatorBase):
    def test_not_initialized_when_config_missing(self):
        emu = AndroidEmulator(
            name="test_emu",
            device="Nexus 4",
            android_version="10.0",
            data_partition="550m",
            extra_args="",
            image_type="google_apis",
            system_image="x86",
        )
        with mock.patch("os.path.exists", return_value=False):
            self.assertFalse(emu.is_initialized())

    def test_not_initialized_when_device_not_in_config(self):
        emu = AndroidEmulator(
            name="test_emu",
            device="Nexus 4",
            android_version="10.0",
            data_partition="550m",
            extra_args="",
            image_type="google_apis",
            system_image="x86",
        )
        with mock.patch("os.path.exists", return_value=True):
            with mock.patch("builtins.open", mock.mock_open(read_data="hw.device.name=Nexus 5\n")):
                self.assertFalse(emu.is_initialized())

    def test_initialized_when_device_matches(self):
        emu = AndroidEmulator(
            name="test_emu",
            device="Nexus 4",
            android_version="10.0",
            data_partition="550m",
            extra_args="",
            image_type="google_apis",
            system_image="x86",
        )
        with mock.patch("os.path.exists", return_value=True):
            with mock.patch("builtins.open", mock.mock_open(read_data="hw.device.name=Nexus 4\n")):
                self.assertTrue(emu.is_initialized())


class TestEmulatorAdbCheck(TestEmulatorBase):
    def test_adb_check_succeeds_on_match(self):
        emu = AndroidEmulator(
            name="test_emu",
            device="Nexus 4",
            android_version="10.0",
            data_partition="550m",
            extra_args="",
            image_type="google_apis",
            system_image="x86",
        )
        with mock.patch("subprocess.check_output", return_value=b"1"):
            emu.run_adb_check(
                emu.BootState.BOOTED,
                "mock_command",
                "1",
                max_tries=3,
                wait_time=0,
            )

    def test_adb_check_fails_after_max_attempts(self):
        emu = AndroidEmulator(
            name="test_emu",
            device="Nexus 4",
            android_version="10.0",
            data_partition="550m",
            extra_args="",
            image_type="google_apis",
            system_image="x86",
        )
        with mock.patch("subprocess.check_output", return_value=b"0"):
            with self.assertRaises(RuntimeError):
                emu.run_adb_check(
                    emu.BootState.BOOTED,
                    "mock_command",
                    "1",
                    max_tries=3,
                    wait_time=0,
                )


class TestEmulatorOverrideConfig(TestEmulatorBase):
    def test_override_skipped_when_env_not_set(self):
        emu = AndroidEmulator(
            name="test_emu",
            device="Nexus 4",
            android_version="10.0",
            data_partition="550m",
            extra_args="",
            image_type="google_apis",
            system_image="x86",
        )
        with mock.patch.dict(os.environ, {}, clear=False):
            if env_vars.EMU_OVERRIDE_CONFIG in os.environ:
                del os.environ[env_vars.EMU_OVERRIDE_CONFIG]
            emu._apply_override_config()

    def test_override_skipped_when_file_missing(self):
        emu = AndroidEmulator(
            name="test_emu",
            device="Nexus 4",
            android_version="10.0",
            data_partition="550m",
            extra_args="",
            image_type="google_apis",
            system_image="x86",
        )
        with mock.patch.dict(os.environ, {env_vars.EMU_OVERRIDE_CONFIG: "/nonexistent/path"}):
            with mock.patch("os.path.isfile", return_value=False):
                emu._apply_override_config()

    def test_override_skipped_when_not_readable(self):
        emu = AndroidEmulator(
            name="test_emu",
            device="Nexus 4",
            android_version="10.0",
            data_partition="550m",
            extra_args="",
            image_type="google_apis",
            system_image="x86",
        )
        with mock.patch.dict(os.environ, {env_vars.EMU_OVERRIDE_CONFIG: "/some/path"}):
            with mock.patch("os.path.isfile", return_value=True):
                with mock.patch("os.access", return_value=False):
                    emu._apply_override_config()


class TestEmulatorStatusWrite(TestEmulatorBase):
    def test_write_status_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ[env_vars.WORK_PATH] = tmpdir
            emu = AndroidEmulator(
                name="test_emu",
                device="Nexus 4",
                android_version="10.0",
                data_partition="550m",
                extra_args="",
                image_type="google_apis",
                system_image="x86",
            )
            emu.write_status("TESTING")

            status_file = os.path.join(tmpdir, "device_status")
            self.assertTrue(os.path.exists(status_file))
            with open(status_file) as f:
                self.assertEqual(f.read(), "TESTING")
