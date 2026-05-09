# Todo

## Plan
Build the CLI from the inside out: start with the core device management features (emulator, helpers), then add Genymotion cloud integrations, and finally the CLI layer that ties everything together. Each task delivers a complete, testable feature.

## Tasks
- [x] Task 1: Create helper utilities for environment variable retrieval, string-to-boolean conversion, and symlink creation. These form the foundation used throughout the application.
- [x] Task 2: Build the Android emulator device manager that validates device profiles and Android versions, checks initialization status, creates emulators with AVD manager, configures skins and device profiles, and monitors readiness via ADB commands.
- [x] Task 3: Implement the Genymotion SaaS integration that handles authentication (via token or credentials), reads device templates from JSON, creates instances in parallel, connects via ADB, and provides cleanup on shutdown.
- [x] Task 4: Implement the Genymotion AWS integration that manages AWS credentials, generates Terraform configurations for deploying Genymotion devices, handles SSH key creation, deploys infrastructure, and connects via local ADB tunnels.
- [x] Task 5: Build the application process manager that can start external programs with optional xterm UI, supporting services like Appium, VNC server, display managers, and port forwarders.
- [>] Task 6: Create the main CLI with Click commands for starting devices, Appium, display services, VNC server/web, port forwarder, and a log sharing HTTP server.
