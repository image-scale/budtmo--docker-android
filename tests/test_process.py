from unittest import TestCase, mock

from android_runner.process import ProcessRunner, ServiceKind


class TestProcessRunner(TestCase):
    def test_create_with_name_and_command(self):
        runner = ProcessRunner(name="test_app", command="/usr/bin/test")
        self.assertEqual(runner.name, "test_app")
        self.assertEqual(runner.command, "/usr/bin/test")
        self.assertEqual(runner.extra_args, "")
        self.assertFalse(runner.use_terminal)

    def test_create_with_args(self):
        runner = ProcessRunner(
            name="app",
            command="/bin/run",
            extra_args="--verbose --debug",
        )
        self.assertEqual(runner.extra_args, "--verbose --debug")

    def test_start_without_terminal(self):
        runner = ProcessRunner(
            name="bg_app",
            command="/usr/bin/app",
            extra_args="-d",
            use_terminal=False,
        )

        with mock.patch("subprocess.check_call") as mock_call:
            runner.start()

        call_args = mock_call.call_args[0][0]
        self.assertIn("/usr/bin/app", call_args)
        self.assertIn("-d", call_args)
        self.assertNotIn("xterm", call_args)

    def test_start_with_terminal(self):
        runner = ProcessRunner(
            name="ui_app",
            command="/usr/bin/gui",
            extra_args="--window",
            use_terminal=True,
        )

        with mock.patch("subprocess.check_call") as mock_call:
            runner.start()

        call_args = mock_call.call_args[0][0]
        self.assertIn("xterm", call_args)
        self.assertIn("-T ui_app", call_args)
        self.assertIn("/usr/bin/gui", call_args)

    def test_repr(self):
        runner = ProcessRunner(
            name="repr_app",
            command="/bin/test",
            extra_args="--flag",
            use_terminal=True,
        )

        repr_str = repr(runner)
        self.assertIn("repr_app", repr_str)
        self.assertIn("/bin/test", repr_str)
        self.assertIn("--flag", repr_str)
        self.assertIn("terminal=True", repr_str)


class TestServiceKind(TestCase):
    def test_service_kinds_exist(self):
        self.assertEqual(ServiceKind.APPIUM.value, "appium")
        self.assertEqual(ServiceKind.DEVICE.value, "device")
        self.assertEqual(ServiceKind.DISPLAY_SCREEN.value, "display_screen")
        self.assertEqual(ServiceKind.DISPLAY_WM.value, "display_wm")
        self.assertEqual(ServiceKind.PORT_FORWARDER.value, "port_forwarder")
        self.assertEqual(ServiceKind.VNC_SERVER.value, "vnc_server")
        self.assertEqual(ServiceKind.VNC_WEB.value, "vnc_web")
