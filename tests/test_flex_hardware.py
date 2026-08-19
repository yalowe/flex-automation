from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import allure
import pytest

from main import main
from reporting.allure_reporter import AllureReporter

ROOT = Path(__file__).resolve().parents[1]
LOGS_ROOT = ROOT / "logs"


def _session_dirs_before_run() -> set[Path]:
    if not LOGS_ROOT.exists():
        return set()
    return {path for path in LOGS_ROOT.iterdir() if path.is_dir()}


def _newest_session(before: set[Path]) -> Path | None:
    candidates = (
        [path for path in LOGS_ROOT.iterdir() if path.is_dir() and path not in before]
        if LOGS_ROOT.exists()
        else []
    )
    return (
        max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None
    )


@pytest.mark.hardware
@allure.epic("FLEX hardware automation")
@allure.feature("Controller scenarios")
def test_flex_scenarios(flex_cli_options):
    before = _session_dirs_before_run()
    reporter = AllureReporter(flex_cli_options["allure_dir"])
    args = SimpleNamespace(
        port=flex_cli_options["port"],
        baud=flex_cli_options["baud"],
        runs=flex_cli_options["runs"],
        dry_run_config=False,
    )

    allure.dynamic.parameter("serial_port", args.port)
    allure.dynamic.parameter("baud", args.baud)
    allure.dynamic.parameter("runs", args.runs)

    try:
        with reporter.capture_console() as console:
            stats = main(args)
        allure.dynamic.title(reporter.rich_title(console.getvalue()))
        failed = {
            scenario: result
            for scenario, result in (stats or {}).items()
            if result.get("fail", 0) > 0
        }
        if failed:
            raise AssertionError(f"FLEX scenario failures: {failed}")
    except Exception as exc:
        session_dir = _newest_session(before)
        allure.dynamic.title(reporter.rich_title(reporter.console.getvalue()))
        reporter.publish(
            args=args,
            session_dir=session_dir,
            output=reporter.console.getvalue(),
            error=exc,
        )
        raise
    else:
        reporter.publish(
            args=args,
            session_dir=_newest_session(before),
            output=reporter.console.getvalue(),
        )
