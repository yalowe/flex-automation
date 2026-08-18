from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
POLICY = REPO_ROOT / "scripts" / "headless_monitor_policy.py"
TMP_DIR = REPO_ROOT / "logs" / "_smoke_headless_policy"


def _write_fixture() -> None:
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    (TMP_DIR / "scenario_monitoring_summary.txt").write_text(
        "\n"
        "scenario=Spread By Quantity\n"
        "summary lines=20 device_events=8 valve_open=2 valve_close=2 wm_events=4 anomalies=0\n",
        encoding="utf-8",
    )

    (TMP_DIR / "anomalies.txt").write_text(
        "[2026-01-01 00:00:00] (IrrCmd Set 5 7) flow_alarm_pattern | line=Low Flow Alarm\n",
        encoding="utf-8",
    )


def _run(policy: str) -> int:
    cmd = [
        str(PYTHON),
        str(POLICY),
        "--policy",
        policy,
        "--session-dir",
        str(TMP_DIR),
        "--scenario-name",
        "Spread By Quantity",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())
    return result.returncode


def main() -> None:
    _write_fixture()

    rc_safe = _run("safe")
    assert rc_safe == 0, f"safe policy expected PASS, got rc={rc_safe}"

    rc_strict = _run("strict")
    assert rc_strict != 0, "strict policy expected FAIL due to blocked anomaly"

    rc_lab = _run("lab")
    assert rc_lab == 0, f"lab policy expected PASS, got rc={rc_lab}"

    print("smoke_headless_monitor_policy: PASS")


if __name__ == "__main__":
    main()
