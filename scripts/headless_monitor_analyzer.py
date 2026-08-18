from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys


@dataclass
class ScenarioSummary:
    scenario: str
    lines: int
    device_events: int
    valve_open: int
    valve_close: int
    wm_events: int
    anomalies: int


def _parse_summary_line(summary_line: str) -> dict[str, int]:
    values: dict[str, int] = {}
    for token in summary_line.strip().split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        try:
            values[key.strip()] = int(value.strip())
        except ValueError:
            continue
    return values


def _read_latest_summary(summary_file: Path, scenario_name: str | None) -> ScenarioSummary | None:
    if not summary_file.exists():
        return None

    text = summary_file.read_text(encoding="utf-8", errors="ignore")
    matches = re.finditer(
        r"scenario=(.*?)\r?\nsummary\s+([^\r\n]+)",
        text,
        re.IGNORECASE,
    )

    candidates: list[ScenarioSummary] = []
    for match in matches:
        scenario = match.group(1).strip()
        values = _parse_summary_line(match.group(2))

        candidates.append(
            ScenarioSummary(
                scenario=scenario,
                lines=values.get("lines", 0),
                device_events=values.get("device_events", 0),
                valve_open=values.get("valve_open", 0),
                valve_close=values.get("valve_close", 0),
                wm_events=values.get("wm_events", 0),
                anomalies=values.get("anomalies", 0),
            )
        )

    if not candidates:
        return None

    if scenario_name:
        filtered = [c for c in candidates if c.scenario == scenario_name]
        if filtered:
            return filtered[-1]

    return candidates[-1]


def _read_anomaly_types(anomalies_file: Path) -> dict[str, int]:
    if not anomalies_file.exists():
        return {}

    counts: dict[str, int] = {}
    pattern = re.compile(r"\)\s+([a-z_]+)\s+\|", re.IGNORECASE)

    for line in anomalies_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = pattern.search(line)
        if not match:
            continue
        anomaly_type = match.group(1).strip().lower()
        counts[anomaly_type] = counts.get(anomaly_type, 0) + 1

    return counts


def analyze_session(args: argparse.Namespace) -> tuple[bool, list[str]]:
    session_dir = Path(args.session_dir)
    issues: list[str] = []

    if not session_dir.exists():
        return False, [f"session directory not found: {session_dir}"]

    summary = _read_latest_summary(
        session_dir / "scenario_monitoring_summary.txt",
        args.scenario_name,
    )

    if summary is None:
        issues.append("scenario summary not found")
    else:
        effective_anomaly_count = (
            args.anomaly_count
            if args.anomaly_count is not None
            else summary.anomalies
        )

        if args.max_anomalies >= 0 and effective_anomaly_count > args.max_anomalies:
            issues.append(
                "anomaly threshold exceeded: "
                f"count={effective_anomaly_count} max={args.max_anomalies}"
            )

        if summary.device_events < args.min_device_events:
            issues.append(
                "device events below threshold: "
                f"device_events={summary.device_events} min={args.min_device_events}"
            )

        if args.require_wm_events and summary.wm_events <= 0:
            issues.append("wm events required but none found")

        if args.require_valve_events and (summary.valve_open + summary.valve_close) <= 0:
            issues.append("valve events required but none found")

    blocked_types = [
        item.strip().lower()
        for item in args.blocked_anomalies.split(",")
        if item.strip()
    ]

    if blocked_types:
        anomaly_counts = _read_anomaly_types(session_dir / "anomalies.txt")
        for blocked in blocked_types:
            count = anomaly_counts.get(blocked, 0)
            if count > 0:
                issues.append(
                    "blocked anomaly detected: "
                    f"type={blocked} count={count}"
                )

    return len(issues) == 0, issues


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze monitoring session output for pass/fail gating.",
    )
    parser.add_argument("--session-dir", required=True, help="Path to logs session directory")
    parser.add_argument("--scenario-name", default=None, help="Scenario name to analyze")
    parser.add_argument("--program-id", type=int, default=None, help="Program ID (optional metadata)")
    parser.add_argument("--anomaly-count", type=int, default=None, help="Scenario anomaly count from runtime summary")
    parser.add_argument("--max-anomalies", type=int, default=0, help="Max allowed anomalies (-1 disables threshold)")
    parser.add_argument("--min-device-events", type=int, default=1, help="Minimum required device events")
    parser.add_argument("--require-wm-events", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--require-valve-events", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument(
        "--blocked-anomalies",
        default="",
        help="Comma-separated anomaly types that should fail (example: command_error,flow_alarm_pattern)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    ok, issues = analyze_session(args)

    print("headless_monitor_analyzer summary:")
    print(f"- session_dir: {args.session_dir}")
    if args.scenario_name:
        print(f"- scenario_name: {args.scenario_name}")
    if args.program_id is not None:
        print(f"- program_id: {args.program_id}")

    if ok:
        print("- result: PASS")
        return 0

    print("- result: FAIL")
    for issue in issues:
        print(f"  * {issue}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
