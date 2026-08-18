"""Consolidated smoke tests for the headless analyzer hook and its policy wrapper.

Merged from (each check preserves the original assertions verbatim):
smoke_headless_hook, smoke_headless_monitor_analyzer, smoke_headless_monitor_policy.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runner.programs_and_dosings import _run_headless_analyzer_hook

PYTHON = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
ANALYZER = REPO_ROOT / "scripts" / "headless_monitor_analyzer.py"
POLICY = REPO_ROOT / "scripts" / "headless_monitor_policy.py"


def check_headless_hook() -> None:
    os.environ["FLEX_HEADLESS_ANALYZER_CMD"] = (
        "python -c \"print('hook-ok scenario={scenario_name} program={program_id} anomalies={anomaly_count}')\""
    )
    ok, error = _run_headless_analyzer_hook(
        scenario_name="Spread By Quantity",
        program_id=7,
        session_dir="logs/20260817_000000",
        anomaly_count=0,
    )
    assert ok, f"Headless hook should pass, got: {error}"
    print("check_headless_hook: PASS")


def _write_monitoring_fixture(tmp_dir: Path, anomalies: int) -> None:
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    (tmp_dir / "scenario_monitoring_summary.txt").write_text(
        "\nscenario=Spread By Quantity\n"
        f"summary lines=20 device_events=8 valve_open=2 valve_close=2 wm_events=4 anomalies={anomalies}\n",
        encoding="utf-8",
    )
    (tmp_dir / "anomalies.txt").write_text(
        "[2026-01-01 00:00:00] (IrrCmd Set 5 7) flow_alarm_pattern | line=Low Flow Alarm\n",
        encoding="utf-8",
    )


def check_headless_monitor_analyzer() -> None:
    tmp_dir = REPO_ROOT / "logs" / "_smoke_headless_analyzer"
    _write_monitoring_fixture(tmp_dir, anomalies=0)

    def run(args):
        cmd = [str(PYTHON), str(ANALYZER)] + args
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.stderr.strip():
            print(result.stderr.strip())
        return result.returncode

    rc_pass = run(
        [
            "--session-dir",
            str(tmp_dir),
            "--scenario-name",
            "Spread By Quantity",
            "--max-anomalies",
            "0",
        ]
    )
    assert rc_pass == 0, f"Expected pass exit code 0, got {rc_pass}"

    rc_fail = run(
        [
            "--session-dir",
            str(tmp_dir),
            "--scenario-name",
            "Spread By Quantity",
            "--max-anomalies",
            "0",
            "--blocked-anomalies",
            "flow_alarm_pattern",
        ]
    )
    assert rc_fail != 0, "Expected fail exit code for blocked anomaly"
    print("check_headless_monitor_analyzer: PASS")


def check_headless_monitor_policy() -> None:
    tmp_dir = REPO_ROOT / "logs" / "_smoke_headless_policy"
    _write_monitoring_fixture(tmp_dir, anomalies=0)

    def run(policy: str) -> int:
        cmd = [
            str(PYTHON),
            str(POLICY),
            "--policy",
            policy,
            "--session-dir",
            str(tmp_dir),
            "--scenario-name",
            "Spread By Quantity",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.stderr.strip():
            print(result.stderr.strip())
        return result.returncode

    rc_safe = run("safe")
    assert rc_safe == 0, f"safe policy expected PASS, got rc={rc_safe}"

    rc_strict = run("strict")
    assert rc_strict != 0, "strict policy expected FAIL due to blocked anomaly"

    rc_lab = run("lab")
    assert rc_lab == 0, f"lab policy expected PASS, got rc={rc_lab}"
    print("check_headless_monitor_policy: PASS")


CHECKS = [
    check_headless_hook,
    check_headless_monitor_analyzer,
    check_headless_monitor_policy,
]


def main() -> None:
    for check in CHECKS:
        check()
    print("smoke_headless_hook_suite: ALL PASS")


if __name__ == "__main__":
    main()
