from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re


@dataclass
class MonitorEvent:
    timestamp: str
    category: str
    line: str
    source_command: str


@dataclass
class ParsedDeviceEvent:
    timestamp: str
    device_type: str
    device_id: int
    action: str
    count: int
    wm_snapshot: dict[int, int]
    source_command: str
    raw_line: str


class MonitoringService:
    """Collects controller output and stores categorized events per run session."""

    CATEGORY_FILES = {
        "app_event": "app_events.txt",
        "water_meter": "water_meter_events.txt",
        "dosing": "dosing_events.txt",
        "irrigation": "irrigation_events.txt",
        "alarm": "alarm_events.txt",
        "battery": "battery_events.txt",
        "general": "general_events.txt",
        "anomaly": "anomalies.txt",
    }

    def __init__(self, logs_root: str = "logs"):
        self.logs_root = Path(logs_root)
        self.session_dir: Path | None = None
        self.monitor_events: list[MonitorEvent] = []
        self.device_events: list[ParsedDeviceEvent] = []
        self.anomalies: list[tuple[str, str, str, str]] = []
        self.event_pattern = re.compile(r"\[(\d{2}:\d{2}:\d{2})\]\s+(valve|wm)\s+(\d+)\s+(.+)")
        self.nucleo_time_re = re.compile(r" at (\d{2}:\d{2}:\d{2})")
        self.wm_snapshot_re = re.compile(r"wm(\d+)=(\d+)")
        self.count_re = re.compile(r"count\s+(\d+)")

    def start_session(self) -> Path:
        session_name = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.logs_root / session_name
        self.session_dir.mkdir(parents=True, exist_ok=True)

        for filename in self.CATEGORY_FILES.values():
            self._append(filename, "")

        return self.session_dir

    def capture(self, command: str, response: str, success: bool) -> list[MonitorEvent]:
        if self.session_dir is None:
            self.start_session()

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._append(
            "raw_commands.txt",
            f"\n[{timestamp}] command={command} success={success}\n{response.rstrip()}\n",
        )

        events: list[MonitorEvent] = []

        for raw_line in response.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            category = self._categorize_line(line)
            event = MonitorEvent(
                timestamp=timestamp,
                category=category,
                line=line,
                source_command=command,
            )
            events.append(event)
            self.monitor_events.append(event)

            parsed_device_event = self._parse_device_event(
                timestamp=timestamp,
                command=command,
                line=line,
            )
            if parsed_device_event is not None:
                self.device_events.append(parsed_device_event)

            self._append(
                self.CATEGORY_FILES[category],
                f"[{timestamp}] ({command}) {line}\n",
            )

            anomaly = self._detect_anomaly(line)
            if anomaly:
                self.anomalies.append((timestamp, command, anomaly, line))
                self._append(
                    self.CATEGORY_FILES["anomaly"],
                    f"[{timestamp}] ({command}) {anomaly} | line={line}\n",
                )

        return events

    def mark(self) -> dict[str, int]:
        return {
            "monitor_events": len(self.monitor_events),
            "device_events": len(self.device_events),
            "anomalies": len(self.anomalies),
        }

    def summarize_since(self, marker: dict[str, int], scenario_name: str) -> dict:
        monitor_from = marker.get("monitor_events", 0)
        device_from = marker.get("device_events", 0)
        anomaly_from = marker.get("anomalies", 0)

        new_monitor_events = self.monitor_events[monitor_from:]
        new_device_events = self.device_events[device_from:]
        new_anomalies = self.anomalies[anomaly_from:]

        valve_open_count = 0
        valve_close_count = 0
        wm_event_count = 0
        wm_last_counts: dict[int, int] = {}

        for event in new_device_events:
            if event.device_type == "valve":
                if "open" in event.action:
                    valve_open_count += 1
                if "close" in event.action:
                    valve_close_count += 1

            if event.device_type == "wm":
                wm_event_count += 1
                if event.count > 0:
                    wm_last_counts[event.device_id] = event.count

        summary = {
            "scenario": scenario_name,
            "lines": len(new_monitor_events),
            "device_events": len(new_device_events),
            "valve_open_count": valve_open_count,
            "valve_close_count": valve_close_count,
            "wm_event_count": wm_event_count,
            "wm_last_counts": wm_last_counts,
            "anomaly_count": len(new_anomalies),
            "anomalies": new_anomalies,
        }

        self._append(
            "scenario_monitoring_summary.txt",
            self._format_summary(summary),
        )

        return summary

    def _append(self, filename: str, content: str) -> None:
        if self.session_dir is None:
            raise RuntimeError("Monitoring session is not started")

        path = self.session_dir / filename
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(content)

    @staticmethod
    def _categorize_line(line: str) -> str:
        lower_line = line.lower()

        if re.search(r"\bbattery\b|\bbatt\b", lower_line):
            return "battery"

        if re.search(r"\balarm\b|\balert\b|\bfault\b", lower_line):
            return "alarm"

        if re.search(r"\bapp\s*event\b|\bevent\b", lower_line):
            return "app_event"

        if re.search(r"\bwm\d*\b|water\s*meter|pulse", lower_line):
            return "water_meter"

        if re.search(r"\bdosing\b|\bfert\w*\b|\bdm\d\b", lower_line):
            return "dosing"

        if re.search(r"\bvalve\b|\birrig\w*\b|\bshift\b|\bprogram\b", lower_line):
            return "irrigation"

        return "general"

    @staticmethod
    def _detect_anomaly(line: str) -> str | None:
        lower_line = line.lower()

        if "status:error" in lower_line:
            return "command_error"

        if "battery recovery" in lower_line:
            return "battery_recovery_state"

        if re.search(r"\bno flow\b|\blow flow\b|\bhigh flow\b|flow mismatch", lower_line):
            return "flow_alarm_pattern"

        return None

    def _parse_device_event(
        self,
        timestamp: str,
        command: str,
        line: str,
    ) -> ParsedDeviceEvent | None:
        match = self.event_pattern.search(line)
        if not match:
            return None

        _, device_type, device_id_text, raw_action = match.groups()
        action_text = raw_action.strip()

        nucleo_time = self.nucleo_time_re.search(action_text)
        if nucleo_time:
            action_text = action_text[:nucleo_time.start()].strip()

        wm_snapshot: dict[int, int] = {}
        if "|" in raw_action:
            snapshot_part = raw_action[raw_action.index("|") + 1:]
            for snapshot_match in self.wm_snapshot_re.finditer(snapshot_part):
                wm_snapshot[int(snapshot_match.group(1))] = int(snapshot_match.group(2))

        count = 0
        count_match = self.count_re.search(action_text.lower())
        if count_match:
            count = int(count_match.group(1))

        return ParsedDeviceEvent(
            timestamp=timestamp,
            device_type=device_type.lower(),
            device_id=int(device_id_text),
            action=action_text.lower(),
            count=count,
            wm_snapshot=wm_snapshot,
            source_command=command,
            raw_line=line,
        )

    @staticmethod
    def _format_summary(summary: dict) -> str:
        lines = [
            "",
            f"scenario={summary['scenario']}",
            (
                "summary "
                f"lines={summary['lines']} "
                f"device_events={summary['device_events']} "
                f"valve_open={summary['valve_open_count']} "
                f"valve_close={summary['valve_close_count']} "
                f"wm_events={summary['wm_event_count']} "
                f"anomalies={summary['anomaly_count']}"
            ),
        ]

        if summary["wm_last_counts"]:
            wm_state = ", ".join(
                f"wm{wm_id}={count}"
                for wm_id, count in sorted(summary["wm_last_counts"].items())
            )
            lines.append(f"wm_last_counts {wm_state}")

        for anomaly in summary["anomalies"]:
            timestamp, command, anomaly_type, line = anomaly
            lines.append(
                f"anomaly [{timestamp}] ({command}) {anomaly_type} | line={line}"
            )

        return "\n".join(lines) + "\n"
