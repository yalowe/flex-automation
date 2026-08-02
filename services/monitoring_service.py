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

            self._append(
                self.CATEGORY_FILES[category],
                f"[{timestamp}] ({command}) {line}\n",
            )

            anomaly = self._detect_anomaly(line)
            if anomaly:
                self._append(
                    self.CATEGORY_FILES["anomaly"],
                    f"[{timestamp}] ({command}) {anomaly} | line={line}\n",
                )

        return events

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
