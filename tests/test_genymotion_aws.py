import json
import os
import tempfile
from unittest import TestCase, mock

from android_runner.genymotion_aws import GenymotionAws
from android_runner import env_vars


class TestGenymotionAwsBase(TestCase):
    """Base test class for Genymotion AWS tests."""

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


class TestGenymotionAwsCredentials(TestGenymotionAwsBase):
    def test_uses_existing_credentials(self):
        os.makedirs(os.path.join(self.temp_dir, ".aws"))
        geny = GenymotionAws()

        geny._login()

        self.assertFalse(geny.should_cleanup_creds)

    def test_creates_credentials_from_template(self):
        templates_dir = os.path.join(
            self.temp_dir, "docker-android", "mixins", "templates", "genymotion", "aws", ".aws"
        )
        os.makedirs(templates_dir)
        creds_file = os.path.join(templates_dir, "credentials")
        with open(creds_file, "w") as f:
            f.write("<aws_access_key_id>\n<aws_secret_access_key>")

        os.environ[env_vars.AWS_KEY_ID] = "AKIATEST123"
        os.environ[env_vars.AWS_SECRET_KEY] = "secretkey456"

        geny = GenymotionAws()
        geny._login()

        self.assertTrue(geny.should_cleanup_creds)

        new_creds_file = os.path.join(self.temp_dir, ".aws", "credentials")
        with open(new_creds_file) as f:
            content = f.read()
            self.assertIn("AKIATEST123", content)
            self.assertIn("secretkey456", content)

        del os.environ[env_vars.AWS_KEY_ID]
        del os.environ[env_vars.AWS_SECRET_KEY]


class TestGenymotionAwsSshKey(TestGenymotionAwsBase):
    def test_generates_ssh_key(self):
        geny = GenymotionAws()

        with mock.patch("subprocess.check_call") as mock_call:
            geny._generate_ssh_key()

        call_args = mock_call.call_args[0][0]
        self.assertIn("ssh-keygen", call_args)
        self.assertIn("-t rsa", call_args)
        self.assertIn("-b 4096", call_args)


class TestGenymotionAwsTerraform(TestGenymotionAwsBase):
    def test_generates_tf_with_security_group(self):
        template_data = [{
            "name": "device1",
            "region": "us-east-1",
            "ami": "ami-123",
            "instance_type": "t2.micro",
            "security_group": "sg-abc123",
        }]
        template_file = os.path.join(self.temp_dir, "aws.json")
        with open(template_file, "w") as f:
            json.dump(template_data, f)

        geny = GenymotionAws()
        geny._generate_terraform_files()

        self.assertIn("device1", geny.devices)
        self.assertTrue(os.path.exists("device1.tf"))

        with open("device1.tf") as f:
            content = f.read()
            self.assertIn("us-east-1", content)
            self.assertIn("ami-123", content)
            self.assertIn("sg-abc123", content)

        os.remove("device1.tf")

    def test_generates_tf_with_rules(self):
        template_data = [{
            "name": "device2",
            "region": "eu-west-1",
            "ami": "ami-456",
            "instance_type": "t3.small",
            "ingress_rules": [{"from_port": 22, "to_port": 22, "protocol": "tcp", "cidr_blocks": ["0.0.0.0/0"]}],
            "egress_rules": [{"from_port": 0, "to_port": 0, "protocol": "-1", "cidr_blocks": ["0.0.0.0/0"]}],
        }]
        template_file = os.path.join(self.temp_dir, "aws.json")
        with open(template_file, "w") as f:
            json.dump(template_data, f)

        geny = GenymotionAws()
        geny._generate_terraform_files()

        self.assertTrue(os.path.exists("device2.tf"))

        with open("device2.tf") as f:
            content = f.read()
            self.assertIn("aws_security_group", content)
            self.assertIn("ingress_rules", content)
            self.assertIn("egress_rules", content)

        os.remove("device2.tf")

    def test_assigns_unique_ports(self):
        template_data = [
            {"name": "dev1", "region": "us-east-1", "ami": "ami-1", "instance_type": "t2.micro", "security_group": "sg-1"},
            {"name": "dev2", "region": "us-east-1", "ami": "ami-2", "instance_type": "t2.micro", "security_group": "sg-2"},
        ]
        template_file = os.path.join(self.temp_dir, "aws.json")
        with open(template_file, "w") as f:
            json.dump(template_data, f)

        geny = GenymotionAws()
        geny._generate_terraform_files()

        ports = list(geny.devices.values())
        self.assertEqual(len(set(ports)), 2)

        os.remove("dev1.tf")
        os.remove("dev2.tf")


class TestGenymotionAwsDeploy(TestGenymotionAwsBase):
    def test_runs_terraform_commands(self):
        geny = GenymotionAws()

        with mock.patch("subprocess.check_call") as mock_call:
            geny._deploy_terraform()

        calls = [c[0][0] for c in mock_call.call_args_list]
        self.assertIn("terraform init", calls)
        self.assertIn("terraform plan", calls)
        self.assertIn("terraform apply -auto-approve", calls)


class TestGenymotionAwsAdb(TestGenymotionAwsBase):
    def test_connects_adb_via_tunnel(self):
        geny = GenymotionAws()
        geny.devices = {"test_device": 5557}

        with mock.patch("subprocess.check_output", return_value=b'"test.example.com"\n'):
            with mock.patch("subprocess.Popen") as mock_popen:
                with mock.patch("subprocess.check_call") as mock_call:
                    with mock.patch("time.sleep"):
                        geny._connect_adb()

        tunnel_args = mock_popen.call_args[0][0]
        self.assertIn("ssh", tunnel_args)
        self.assertIn("-NL", tunnel_args)

        adb_call = mock_call.call_args[0][0]
        self.assertIn("adb connect", adb_call)


class TestGenymotionAwsShutdown(TestGenymotionAwsBase):
    def test_destroys_resources(self):
        geny = GenymotionAws()

        with mock.patch("subprocess.check_call") as mock_call:
            geny._shutdown_and_logout()

        call_args = mock_call.call_args[0][0]
        self.assertIn("terraform destroy", call_args)

    def test_cleans_up_credentials(self):
        geny = GenymotionAws()
        geny.should_cleanup_creds = True

        os.makedirs(geny.credentials_path)

        with mock.patch("subprocess.check_call") as mock_call:
            geny._shutdown_and_logout()

        calls = [c[0][0] for c in mock_call.call_args_list]
        cleanup_call = [c for c in calls if "rm -rf" in c and ".aws" in c]
        self.assertEqual(len(cleanup_call), 1)
