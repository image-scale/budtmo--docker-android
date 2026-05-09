# Goal

## Project
docker-android — a python project.

## Description
A CLI tool for managing Android emulators and Genymotion cloud devices within Docker containers. The tool provides commands to start various services including Android emulators (with device profiles and skins), Appium servers, VNC servers for remote viewing, display managers, and port forwarding. It also supports cloud-based Genymotion devices on both SaaS and AWS platforms.

## Scope
- 8 production source files to implement
- 3 test files to write
- Core functionality includes:
  - Helper utilities for environment variables and string conversion
  - Device abstraction with statuses and lifecycle management
  - Android emulator creation, configuration, and readiness checking
  - Genymotion SaaS and AWS device integrations
  - Application process management
  - CLI with Click-based commands for starting services and sharing logs
