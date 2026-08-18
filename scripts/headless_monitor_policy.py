from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYZER = REPO_ROOT / "scripts" / "headless_monitor_analyzer.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run headless monitor analyzer using named policy presets.",
    )
    parser.add_argument("--policy", choices=["safe", "strict", "lab"], default="safe")
    parser.add_argument("--session-dir", required=True)
    parser.add_argument("--scenario-name", default=None)
    parser.add_argument("--program-id", type=int, default=None)
    parser.add_argument("--anomaly-count", type=int, default=None)
    parser.add_argument(
        "--python", default=sys.executable, help="Python executable to run analyzer"
    )
    parser.add_argument(
        "--max-anomalies", type=int, default=None, help="Override policy"
    )
    parser.add_argument(
        "--min-device-events", type=int, default=None, help="Override policy"
    )
    parser.add_argument(
        "--require-wm-events", action=argparse.BooleanOptionalAction, default=None
    )
    parser.add_argument(
        "--require-valve-events", action=argparse.BooleanOptionalAction, default=None
    )
    parser.add_argument("--blocked-anomalies", default=None, help="Override policy")
    return parser.parse_args()


def _policy_defaults(policy: str) -> dict[str, object]:
    if policy == "strict":
        return {
            "max_anomalies": 0,
            "min_device_events": 5,
            "require_wm_events": True,
            "require_valve_events": True,
            "blocked_anomalies": "command_error,flow_alarm_pattern,battery_recovery_state",
        }

    if policy == "lab":
        return {
            "max_anomalies": -1,
            "min_device_events": 0,
            "require_wm_events": False,
            "require_valve_events": False,
            "blocked_anomalies": "",
        }

    return {
        "max_anomalies": -1,
        "min_device_events": 1,
        "require_wm_events": False,
        "require_valve_events": False,
        "blocked_anomalies": "command_error",
    }


def main() -> int:
    args = parse_args()

    defaults = _policy_defaults(args.policy)
    max_anomalies = (
        args.max_anomalies
        if args.max_anomalies is not None
        else defaults["max_anomalies"]
    )
    min_device_events = (
        args.min_device_events
        if args.min_device_events is not None
        else defaults["min_device_events"]
    )
    require_wm_events = (
        args.require_wm_events
        if args.require_wm_events is not None
        else defaults["require_wm_events"]
    )
    require_valve_events = (
        args.require_valve_events
        if args.require_valve_events is not None
        else defaults["require_valve_events"]
    )
    blocked_anomalies = (
        args.blocked_anomalies
        if args.blocked_anomalies is not None
        else defaults["blocked_anomalies"]
    )

    cmd = [
        args.python,
        str(ANALYZER),
        "--session-dir",
        args.session_dir,
        "--max-anomalies",
        str(max_anomalies),
        "--min-device-events",
        str(min_device_events),
    ]

    if args.scenario_name:
        cmd.extend(["--scenario-name", args.scenario_name])
    if args.program_id is not None:
        cmd.extend(["--program-id", str(args.program_id)])
    if args.anomaly_count is not None:
        cmd.extend(["--anomaly-count", str(args.anomaly_count)])
    if require_wm_events:
        cmd.append("--require-wm-events")
    else:
        cmd.append("--no-require-wm-events")
    if require_valve_events:
        cmd.append("--require-valve-events")
    else:
        cmd.append("--no-require-valve-events")
    if blocked_anomalies:
        cmd.extend(["--blocked-anomalies", blocked_anomalies])

    print("headless_monitor_policy: running analyzer")
    print("- policy:", args.policy)
    print("- command:", " ".join(cmd))

    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
