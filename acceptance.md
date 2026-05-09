# Acceptance Criteria

## Task 1: Helper utilities for environment variables, string conversion, and symlinks

### Acceptance Criteria
- [x] `str_to_bool("true")`, `str_to_bool("TRUE")`, `str_to_bool("yes")`, `str_to_bool("1")`, `str_to_bool("t")` return True
- [x] `str_to_bool("false")`, `str_to_bool("no")`, `str_to_bool("0")`, `str_to_bool("f")` return False
- [x] `str_to_bool("")` and `str_to_bool(None)` return False
- [x] `str_to_bool(True)` raises AttributeError (non-string input)
- [x] `require_env("EXISTING_VAR")` returns the environment variable value when set
- [x] `require_env("MISSING_VAR")` raises RuntimeError when the variable is not set
- [x] `require_env("WHITESPACE_VAR")` raises RuntimeError when the variable contains only whitespace
- [x] `create_symlink(source, target)` creates a symlink from target to source
- [x] `create_symlink(source, target)` replaces existing file/symlink at target
- [x] `create_symlink(nonexistent, target)` handles missing source gracefully (creates dangling link or logs error)

## Task 2: Android emulator device manager

### Acceptance Criteria
- [x] Creating an emulator with a supported device ("Nexus 4", "Samsung Galaxy S6", etc.) succeeds
- [x] Creating an emulator with an unsupported device raises RuntimeError
- [x] Creating an emulator with a supported Android version ("10.0", "11.0", etc.) succeeds and sets the correct API level
- [x] Creating an emulator with an unsupported Android version raises RuntimeError
- [x] Each emulator instance gets a unique ADB name (emulator-5554, emulator-5556, etc.)
- [x] Checking initialization returns False when config file doesn't exist
- [x] Checking initialization returns False when config exists but device doesn't match
- [x] Checking initialization returns True when config exists with matching device
- [x] ADB readiness check succeeds when expected keyword is found in output
- [x] ADB readiness check raises RuntimeError after exhausting all attempts
- [x] Override config is skipped when environment variable is not set
- [x] Override config is skipped when specified file doesn't exist
- [x] Override config is skipped when file is not readable
- [x] Device status can be set and persists to file

## Task 3: Genymotion SaaS integration

### Acceptance Criteria
- [ ] Login with auth token calls the correct gmsaas auth token command
- [ ] Login with user/password calls the correct gmsaas auth login command
- [ ] Reading template from valid JSON file returns device configuration
- [ ] Reading template from missing file raises RuntimeError
- [ ] Creating instance from template starts the device via gmsaas
- [ ] Missing template parameter raises RuntimeError
- [ ] Auto-generates name when not specified using UUID
- [ ] Connects to instance ADB after creation
- [ ] Shutdown stops all created instances
- [ ] Logout resets auth when token was used, calls logout otherwise
