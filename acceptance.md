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
- [ ] Creating an emulator with a supported device ("Nexus 4", "Samsung Galaxy S6", etc.) succeeds
- [ ] Creating an emulator with an unsupported device raises RuntimeError
- [ ] Creating an emulator with a supported Android version ("10.0", "11.0", etc.) succeeds and sets the correct API level
- [ ] Creating an emulator with an unsupported Android version raises RuntimeError
- [ ] Each emulator instance gets a unique ADB name (emulator-5554, emulator-5556, etc.)
- [ ] Checking initialization returns False when config file doesn't exist
- [ ] Checking initialization returns False when config exists but device doesn't match
- [ ] Checking initialization returns True when config exists with matching device
- [ ] ADB readiness check succeeds when expected keyword is found in output
- [ ] ADB readiness check raises RuntimeError after exhausting all attempts
- [ ] Override config is skipped when environment variable is not set
- [ ] Override config is skipped when specified file doesn't exist
- [ ] Override config is skipped when file is not readable
- [ ] Device status can be set and persists to file
