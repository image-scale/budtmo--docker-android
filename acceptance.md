# Acceptance Criteria

## Task 1: Helper utilities for environment variables, string conversion, and symlinks

### Acceptance Criteria
- [ ] `str_to_bool("true")`, `str_to_bool("TRUE")`, `str_to_bool("yes")`, `str_to_bool("1")`, `str_to_bool("t")` return True
- [ ] `str_to_bool("false")`, `str_to_bool("no")`, `str_to_bool("0")`, `str_to_bool("f")` return False
- [ ] `str_to_bool("")` and `str_to_bool(None)` return False
- [ ] `str_to_bool(True)` raises AttributeError (non-string input)
- [ ] `require_env("EXISTING_VAR")` returns the environment variable value when set
- [ ] `require_env("MISSING_VAR")` raises RuntimeError when the variable is not set
- [ ] `require_env("WHITESPACE_VAR")` raises RuntimeError when the variable contains only whitespace
- [ ] `create_symlink(source, target)` creates a symlink from target to source
- [ ] `create_symlink(source, target)` replaces existing file/symlink at target
- [ ] `create_symlink(nonexistent, target)` handles missing source gracefully (creates dangling link or logs error)
