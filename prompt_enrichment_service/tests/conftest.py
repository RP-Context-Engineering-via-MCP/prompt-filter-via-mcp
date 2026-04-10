"""
pytest conftest — writes structured test results to test_logs/<timestamp>.log
after every test run.
"""

import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Log directory — sits next to the tests/ folder
# ---------------------------------------------------------------------------
LOG_DIR = Path(__file__).parent.parent / "test_logs"
LOG_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Per-run log file (one file per invocation)
# ---------------------------------------------------------------------------
_run_start: float = 0.0
_log_path: Path | None = None
_file_handler: logging.FileHandler | None = None
_results_header_written: bool = False


def _init_log_file() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return LOG_DIR / f"atce_tests_{stamp}.log"


# ---------------------------------------------------------------------------
# pytest hooks
# ---------------------------------------------------------------------------

def pytest_sessionstart(session):
    global _run_start, _log_path, _file_handler
    _run_start = time.monotonic()
    _log_path = _init_log_file()

    # Write the header block first, then attach the file handler so all
    # subsequent log records appear after the header.
    _write(_log_path, [
        "=" * 72,
        "  ATCE TIER TEST RUN",
        f"  Started : {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"  Log file: {_log_path}",
        "=" * 72,
        "",
        "  ATCE MODULE LOGS",
        "-" * 72,
    ])

    # Attach file handler after the header so module logs follow it
    _file_handler = logging.FileHandler(_log_path, mode="a", encoding="utf-8")
    _file_handler.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"))
    logging.getLogger().addHandler(_file_handler)


def pytest_runtest_logreport(report):
    """Called for setup, call, and teardown phases of each test."""
    global _results_header_written

    if report.when != "call":
        if not report.failed:
            return

    # Write the TEST RESULTS section header once, before the first result line
    if not _results_header_written:
        _write(_log_path, [
            "",
            "  TEST RESULTS",
            "-" * 72,
        ])
        _results_header_written = True

    status = "PASS" if report.passed else ("FAIL" if report.failed else "SKIP")
    duration = f"{report.duration:.4f}s"
    line = f"  [{status}]  {report.nodeid:<70}  {duration}"

    lines = [line]
    if report.failed and report.longreprtext:
        for err_line in report.longreprtext.splitlines():
            lines.append(f"           {err_line}")
        lines.append("")

    _write(_log_path, lines)


def pytest_sessionfinish(session, exitstatus):
    elapsed = time.monotonic() - _run_start

    # Gather counts from the terminal summary stored on the session
    # (terminalreporter plugin stores these)
    passed = failed = skipped = errors = 0
    tr = session.config.pluginmanager.get_plugin("terminalreporter")
    if tr:
        passed  = len(tr.stats.get("passed",  []))
        failed  = len(tr.stats.get("failed",  []))
        skipped = len(tr.stats.get("skipped", []))
        errors  = len(tr.stats.get("error",   []))

    total = passed + failed + skipped + errors
    outcome = "ALL PASSED" if failed == 0 and errors == 0 else "FAILURES DETECTED"

    _write(_log_path, [
        "",
        "-" * 72,
        "  SUMMARY",
        f"  Result  : {outcome}",
        f"  Total   : {total}  |  Passed: {passed}  |  Failed: {failed}  "
        f"|  Skipped: {skipped}  |  Errors: {errors}",
        f"  Duration: {elapsed:.2f}s",
        f"  Finished: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "-" * 72,
    ])

    if _file_handler:
        _file_handler.close()
        logging.getLogger().removeHandler(_file_handler)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _write(path: Path | None, lines: list[str]) -> None:
    if path is None:
        return
    with path.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
