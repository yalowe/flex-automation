from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
ANALYZER = REPO_ROOT / "scripts" / "headless_monitor_analyzer.py"
TMP_DIR = REPO_ROOT / "logs" / "_smoke_headless_analyzer"


def _write_fixture(anomalies: int) -> None:
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    (TMP_DIR / "scenario_monitoring_summary.txt").write_text(
        "\n"
        "scenario=Spread By Quantity\n"
        f"summary lines=20 device_events=8 valve_open=2 valve_close=2 wm_events=4 anomalies={anomalies}\n",
        encoding="utf-8",
    )

    (TMP_DIR / "anomalies.txt").write_text(
        "[2026-01-01 00:00:00] (IrrCmd Set 5 7) flow_alarm_pattern | line=Low Flow Alarm\n",
        encoding="utf-8",
    )


def _run(args: list[str]) -> int:
    cmd = [str(PYTHON), str(ANALYZER)] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())
    return result.returncode


def main() -> None:
    _write_fixture(anomalies=0)

    rc_pass = _run(
        [
            "--session-dir",
            str(TMP_DIR),
            "--scenario-name",
            "Spread By Quantity",
            "--max-anomalies",
            "0",
        ]
    )
    assert rc_pass == 0, f"Expected pass exit code 0, got {rc_pass}"

    rc_fail = _run(
        [
            "--session-dir",
            str(TMP_DIR),
            "--scenario-name",
            "Spread By Quantity",
            "--max-anomalies",
            "0",
            "--blocked-anomalies",
            "flow_alarm_pattern",
        ]
    )
    assert rc_fail != 0, "Expected fail exit code for blocked anomaly"

    print("smoke_headless_monitor_analyzer: PASS")


if __name__ == "__main__":
    main()
