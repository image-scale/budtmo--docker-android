import re


def parse_log(log: str) -> dict[str, str]:
    """Parse test runner output into per-test results.

    Args:
        log: Full stdout+stderr output of `bash run_test.sh 2>&1`.

    Returns:
        Dict mapping test_id to status.
        - test_id: pytest native format, e.g.
          "src/tests/device/test_emulator.py::TestEmulator::test_adb_name"
        - status: one of "PASSED", "FAILED", "SKIPPED", "ERROR"
    """
    results = {}
    # Strip ANSI escape codes
    log = re.sub(r'\x1b\[[0-9;]*m', '', log)

    # Match verbose pytest lines: "path::class::test STATUS [ XX%]"
    # Also handles collection errors: "ERROR path/to/test.py"
    inline_pattern = re.compile(
        r'^((?:\S+::)\S+.*?)\s+(PASSED|FAILED|SKIPPED|ERROR)\s+\[\s*\d+%\]',
        re.MULTILINE
    )
    for m in inline_pattern.finditer(log):
        test_id = m.group(1).strip()
        status = m.group(2)
        results.setdefault(test_id, status)

    # Match summary section lines: "PASSED test_id" or "FAILED test_id - reason"
    summary_pattern = re.compile(
        r'^(PASSED|FAILED|SKIPPED|ERROR)\s+(\S+::\S+)',
        re.MULTILINE
    )
    for m in summary_pattern.finditer(log):
        status = m.group(1)
        test_id = m.group(2)
        results.setdefault(test_id, status)

    # Handle collection errors: "ERROR tests/foo.py" (no "::")
    collection_error_pattern = re.compile(
        r'^ERROR\s+((?:src/)?tests/\S+\.py)\s*$',
        re.MULTILINE
    )
    for m in collection_error_pattern.finditer(log):
        test_id = m.group(1)
        results.setdefault(test_id, 'ERROR')

    return results

