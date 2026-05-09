import json
import logging
import os
import shutil
import subprocess
import time

from android_runner.genymotion_saas import GenymotionBase
from android_runner.device import DeviceKind
from android_runner.utils import require_env
from android_runner import env_vars


ENCODING = "utf-8"


class GenymotionAws(GenymotionBase):
    """Genymotion AWS cloud device manager using Terraform."""

    _next_port = 5555

    def __init__(self) -> None:
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.kind = DeviceKind.GENY_AWS.value
        workdir = require_env(env_vars.WORK_PATH)
        self.credentials_path = os.path.join(workdir, ".aws")
        self.should_cleanup_creds = False
        self.templates_dir = os.path.join(
            workdir, "docker-android", "mixins", "templates", "genymotion", "aws"
        )
        self.devices = {}

    def _login(self) -> None:
        """Set up AWS credentials from existing directory or template."""
        credentials_file = os.path.join(self.credentials_path, "credentials")

        if os.path.exists(self.credentials_path):
            self.logger.info("Using existing AWS credentials")
        else:
            self.logger.info("Creating AWS credentials from template")
            self.should_cleanup_creds = True

            template_creds_path = os.path.join(self.templates_dir, ".aws")
            shutil.move(template_creds_path, self.credentials_path)

            key_id = require_env(env_vars.AWS_KEY_ID)
            secret_key = require_env(env_vars.AWS_SECRET_KEY)

            replacements = {
                f"<{env_vars.AWS_KEY_ID.lower()}>": key_id,
                f"<{env_vars.AWS_SECRET_KEY.lower()}>": secret_key,
            }

            with open(credentials_file, "r+") as f:
                content = f.read()
                for pattern, value in replacements.items():
                    content = content.replace(pattern, value)
                f.seek(0)
                f.write(content)
                f.truncate()

            self.logger.info("AWS credentials configured")

    def _generate_ssh_key(self) -> None:
        """Generate SSH key pair for instance access."""
        subprocess.check_call('ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""', shell=True)
        self.logger.info("SSH key pair created")

    def _generate_terraform_files(self) -> None:
        """Generate Terraform configuration files from templates."""
        try:
            for item in self.load_template(env_vars.GENY_AWS_TEMPLATE):
                name = item["name"]
                region = item["region"]
                ami = item["ami"]
                instance_type = item["instance_type"]

                if "security_group" in item:
                    tf_content = self._generate_tf_with_security_group(
                        name, region, ami, instance_type, item["security_group"]
                    )
                else:
                    tf_content = self._generate_tf_with_rules(
                        name, region, ami, instance_type,
                        item.get("ingress_rules", []),
                        item.get("egress_rules", [])
                    )

                self.devices[name] = GenymotionAws._next_port
                GenymotionAws._next_port += 1

                filename = f"{name}.tf"
                with open(filename, "w") as f:
                    f.write(tf_content)

            self.logger.info("Terraform files generated")
        except Exception as e:
            self.logger.error(e)
            self._shutdown_and_logout()
            raise

    def _generate_tf_with_security_group(
        self, name: str, region: str, ami: str, instance_type: str, sg: str
    ) -> str:
        """Generate Terraform config using existing security group."""
        return f'''
provider "aws" {{
    alias  = "provider_{name}"
    region = "{region}"
}}

resource "aws_key_pair" "geny_key_{name}" {{
    provider = aws.provider_{name}
    public_key = file("~/.ssh/id_rsa.pub")
}}

resource "aws_instance" "geny_aws_{name}" {{
    provider = aws.provider_{name}
    ami = "{ami}"
    instance_type = "{instance_type}"
    vpc_security_group_ids = ["{sg}"]
    key_name = aws_key_pair.geny_key_{name}.key_name
    tags = {{
        Name = "DockerAndroid-GenyAWS-{ami}"
    }}

    provisioner "remote-exec" {{
        connection {{
            type = "ssh"
            user = "shell"
            host = self.public_ip
            private_key = file("~/.ssh/id_rsa")
        }}
        script = "/home/androidusr/docker-android/mixins/scripts/genymotion/aws/enable_adb.sh"
    }}
}}

output "public_dns_{name}" {{
    value = aws_instance.geny_aws_{name}.public_dns
}}
'''

    def _generate_tf_with_rules(
        self, name: str, region: str, ami: str, instance_type: str,
        ingress_rules: list, egress_rules: list
    ) -> str:
        """Generate Terraform config with custom security group rules."""
        ingress_json = json.dumps(ingress_rules)
        egress_json = json.dumps(egress_rules)

        return f'''
locals {{
    ingress_rules = {ingress_json}
    egress_rules = {egress_json}
}}

provider "aws" {{
    alias  = "provider_{name}"
    region = "{region}"
}}

resource "aws_security_group" "geny_sg_{name}" {{
    provider = aws.provider_{name}
    dynamic "ingress" {{
        for_each = local.ingress_rules
        content {{
            from_port   = ingress.value.from_port
            to_port     = ingress.value.to_port
            protocol    = ingress.value.protocol
            cidr_blocks = ingress.value.cidr_blocks
        }}
    }}

    dynamic "egress" {{
        for_each = local.egress_rules
        content {{
            from_port   = egress.value.from_port
            to_port     = egress.value.to_port
            protocol    = egress.value.protocol
            cidr_blocks = egress.value.cidr_blocks
        }}
    }}
}}

resource "aws_key_pair" "geny_key_{name}" {{
    provider = aws.provider_{name}
    public_key = file("~/.ssh/id_rsa.pub")
}}

resource "aws_instance" "geny_aws_{name}" {{
    provider = aws.provider_{name}
    ami = "{ami}"
    instance_type = "{instance_type}"
    vpc_security_group_ids = [aws_security_group.geny_sg_{name}.name]
    key_name = aws_key_pair.geny_key_{name}.key_name
    tags = {{
        Name = "DockerAndroid-GenyAWS-{ami}"
    }}

    provisioner "remote-exec" {{
        connection {{
            type = "ssh"
            user = "shell"
            host = self.public_ip
            private_key = file("~/.ssh/id_rsa")
        }}
        script = "/home/androidusr/docker-android/mixins/scripts/genymotion/aws/enable_adb.sh"
    }}
}}

output "public_dns_{name}" {{
    value = aws_instance.geny_aws_{name}.public_dns
}}
'''

    def _deploy_terraform(self) -> None:
        """Run Terraform to deploy infrastructure."""
        try:
            commands = ("terraform init", "terraform plan", "terraform apply -auto-approve")
            for cmd in commands:
                subprocess.check_call(cmd, shell=True)
            self.logger.info("Genymotion devices deployed on AWS")
        except subprocess.CalledProcessError as e:
            self.logger.error(e)
            self._shutdown_and_logout()
            raise

    def _connect_adb(self) -> None:
        """Create SSH tunnels and connect ADB for all devices."""
        self.logger.info(f"Connecting to devices: {self.devices}")
        try:
            for device_name, port in self.devices.items():
                dns_output = subprocess.check_output(
                    f"terraform output public_dns_{device_name}".split()
                ).decode(ENCODING).replace('"', '').strip()

                tunnel_cmd = (
                    f"ssh -i ~/.ssh/id_rsa -o ServerAliveInterval=60 "
                    f"-o StrictHostKeyChecking=no -q -NL "
                    f"{port}:localhost:5555 shell@{dns_output}"
                )
                subprocess.Popen(tunnel_cmd.split())
                time.sleep(10)
                subprocess.check_call(f"adb connect localhost:{port} >/dev/null 2>&1", shell=True)
                self.logger.info(f"Connected to {device_name} on port {port}")
        except Exception as e:
            self.logger.error(e)
            self._shutdown_and_logout()
            raise

    def create(self) -> None:
        """Create Genymotion devices on AWS."""
        super().create()
        self._generate_ssh_key()
        self._generate_terraform_files()
        self._deploy_terraform()
        self._connect_adb()

    def _shutdown_and_logout(self) -> None:
        """Destroy AWS resources and clean up credentials."""
        try:
            subprocess.check_call("terraform destroy -auto-approve -lock=false", shell=True)
            self.logger.info("AWS resources destroyed")
        except subprocess.CalledProcessError as e:
            self.logger.error(e)
        finally:
            if self.should_cleanup_creds:
                subprocess.check_call(f"rm -rf {self.credentials_path}", shell=True)
                self.logger.info("Cleaned up temporary credentials")
