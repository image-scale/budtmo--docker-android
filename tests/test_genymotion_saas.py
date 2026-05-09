import json
import os
import tempfile
from unittest import TestCase, mock

from android_runner.genymotion_saas import GenymotionBase, GenymotionSaas
from android_runner import env_vars


class TestGenymotionSaasBase(TestCase):
    """Base test class for Genymotion tests."""

    def setUp(self):
        self.env_backup = {}
        self.temp_dir = tempfile.mkdtemp()
        self.required_envs = {
            env_vars.WORK_PATH: self.temp_dir,
            env_vars.ANALYTICS_ENABLED: "false",
            env_vars.GENY_TEMPLATE_PATH: self.temp_dir,
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


class TestGenymotionSaasLogin(TestGenymotionSaasBase):
    def test_login_with_auth_token(self):
        os.environ[env_vars.GENY_AUTH_TOKEN] = "test_token_123"
        geny = GenymotionSaas()

        with mock.patch("subprocess.check_call") as mock_call:
            geny._login()
            mock_call.assert_called_once()
            call_args = mock_call.call_args[0][0]
            self.assertIn("gmsaas auth token test_token_123", call_args)

        del os.environ[env_vars.GENY_AUTH_TOKEN]

    def test_login_with_user_password(self):
        os.environ[env_vars.GENY_SAAS_USER] = "testuser"
        os.environ[env_vars.GENY_SAAS_PASS] = "testpass"

        geny = GenymotionSaas()

        with mock.patch("subprocess.check_call") as mock_call:
            geny._login()
            mock_call.assert_called_once()
            call_args = mock_call.call_args[0][0]
            self.assertIn("gmsaas auth login testuser testpass", call_args)

        del os.environ[env_vars.GENY_SAAS_USER]
        del os.environ[env_vars.GENY_SAAS_PASS]


class TestGenymotionSaasTemplate(TestGenymotionSaasBase):
    def test_load_valid_template(self):
        template_data = [
            {"name": "device1", "template": "tmpl1"},
            {"name": "device2", "template": "tmpl2"},
        ]
        template_file = os.path.join(self.temp_dir, "saas.json")
        with open(template_file, "w") as f:
            json.dump(template_data, f)

        geny = GenymotionSaas()
        result = geny.load_template("saas.json")

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "device1")
        self.assertEqual(result[1]["template"], "tmpl2")

    def test_load_missing_template_raises(self):
        geny = GenymotionSaas()

        with mock.patch.object(geny, "_shutdown_and_logout"):
            with self.assertRaises(RuntimeError) as ctx:
                geny.load_template("nonexistent.json")
            self.assertIn("cannot be found", str(ctx.exception))


class TestGenymotionSaasInstance(TestGenymotionSaasBase):
    def test_start_instance_success(self):
        geny = GenymotionSaas()
        config = {"name": "test_device", "template": "test_template"}

        with mock.patch("subprocess.check_output", return_value=b"instance-id-123\n"):
            with mock.patch("subprocess.check_call"):
                result = geny._start_single_instance(config)

        self.assertEqual(result, {"test_device": "instance-id-123"})

    def test_start_instance_missing_template_raises(self):
        geny = GenymotionSaas()
        config = {"name": "test_device"}

        with self.assertRaises(RuntimeError) as ctx:
            geny._start_single_instance(config)
        self.assertIn("template", str(ctx.exception).lower())

    def test_auto_generate_name_when_not_specified(self):
        geny = GenymotionSaas()
        config = {"template": "test_template"}

        with mock.patch("subprocess.check_output", return_value=b"instance-id-456\n"):
            with mock.patch("subprocess.check_call"):
                result = geny._start_single_instance(config)

        keys = list(result.keys())
        self.assertEqual(len(keys), 1)
        self.assertNotEqual(keys[0], "")

    def test_connect_with_local_port(self):
        geny = GenymotionSaas()
        config = {"name": "test", "template": "tmpl", "local_port": "5555"}

        with mock.patch("subprocess.check_output", return_value=b"inst-id\n"):
            with mock.patch("subprocess.check_call") as mock_call:
                geny._start_single_instance(config)

        call_args = mock_call.call_args[0][0]
        self.assertIn("--adb-serial-port 5555", call_args)


class TestGenymotionSaasShutdown(TestGenymotionSaasBase):
    def test_stop_instance(self):
        geny = GenymotionSaas()
        instance = {"test_device": "instance-123"}

        with mock.patch("subprocess.check_call") as mock_call:
            result = geny._stop_single_instance(instance)

        self.assertTrue(result)
        call_args = mock_call.call_args[0][0]
        self.assertIn("gmsaas instances stop instance-123", call_args)

    def test_logout_with_token(self):
        os.environ[env_vars.GENY_AUTH_TOKEN] = "test_token"
        geny = GenymotionSaas()

        with mock.patch("subprocess.check_call") as mock_call:
            geny._shutdown_and_logout()

        call_args = mock_call.call_args[0][0]
        self.assertIn("gmsaas auth reset", call_args)

        del os.environ[env_vars.GENY_AUTH_TOKEN]

    def test_logout_without_token(self):
        if env_vars.GENY_AUTH_TOKEN in os.environ:
            del os.environ[env_vars.GENY_AUTH_TOKEN]

        geny = GenymotionSaas()

        with mock.patch("subprocess.check_call") as mock_call:
            geny._shutdown_and_logout()

        call_args = mock_call.call_args[0][0]
        self.assertIn("gmsaas auth logout", call_args)
