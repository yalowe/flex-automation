from __future__ import annotations

import io
import json
import platform
import re
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import allure


class _Tee(io.TextIOBase):
    def __init__(self, original, capture):
        self.original = original
        self.capture = capture

    def write(self, value):
        self.original.write(value)
        self.original.flush()
        self.capture.write(value)
        return len(value)

    def flush(self):
        self.original.flush()
        self.capture.flush()


class AllureReporter:
    """Centralizes Allure evidence without changing hardware execution logic."""

    STEP_NAMES = (
        "Connect to controller",
        "Load configuration",
        "Configure program",
        "Configure dosings",
        "Start execution",
        "Monitor execution",
        "Collect reports",
        "Validate results",
        "Cleanup",
    )

    def __init__(self, results_dir: str | Path | None = None):
        self.results_dir = Path(results_dir) if results_dir else None
        self.started_at = datetime.now(timezone.utc)
        self.console = io.StringIO()

    @contextmanager
    def capture_console(self):
        import contextlib

        tee_out = _Tee(sys.stdout, self.console)
        tee_err = _Tee(sys.stderr, self.console)
        with contextlib.redirect_stdout(tee_out), contextlib.redirect_stderr(tee_err):
            yield self.console

    def publish(self, *, args, session_dir: Path | None, output: str, error=None):
        ended_at = datetime.now(timezone.utc)
        self._write_allure_metadata(args=args, ended_at=ended_at)
        self._attach_text("execution.log", output)
        self._attach_environment(args=args, ended_at=ended_at)
        self._attach_steps(output)
        self._attach_summary(output, args=args, ended_at=ended_at, error=error)
        self._attach_validation(output)
        self._attach_session_files(session_dir)
        if error is not None:
            self._attach_text("runner exception", str(error))
            self._attach_text("failure category", self.failure_category(error))

    def _attach_steps(self, output: str):
        """Expose existing console sections as navigable Allure evidence steps."""
        sections = {
            "Connect to controller": "Run settings:",
            "Load configuration": "PROGRAM CONFIG",
            "Configure program": "PROGRAM CONFIG",
            "Configure dosings": "DOSING DIAGNOSTICS",
            "Start execution": "RUNNING:",
            "Monitor execution": "LIVE FLOW",
            "Collect reports": "RESULTS",
            "Validate results": "validation",
            "Cleanup": "Monitoring session:",
        }
        for name in self.STEP_NAMES:
            with allure.step(name):
                marker = sections.get(name)
                excerpt = self._section_excerpt(output, marker) if marker else output[-4000:]
                allure.attach(
                    excerpt or "No matching console section was emitted.",
                    name=f"{name} evidence",
                    attachment_type=allure.attachment_type.TEXT,
                )

    def _attach_summary(self, output: str, *, args, ended_at, error):
        values = self._parse_summary(output)
        values.update(
            {
                "COM port": args.port,
                "Start time": self.started_at.astimezone().isoformat(),
                "End time": ended_at.astimezone().isoformat(),
                "Runtime": str(ended_at - self.started_at),
                "Validation result": "FAIL" if error else values.get("PASS / FAIL", "UNKNOWN"),
                "Total runtime": str(ended_at - self.started_at),
                "Reports collected": str(len(re.findall(r"Report type:\s+(?:Running|Completed)", output, re.IGNORECASE))),
                "Monitoring samples collected": self._first_value(output, "Captured Lines") or "0",
                "Validation count": str(len(self._parse_validation(output))),
                "Passed validations": str(len(self._parse_validation(output))) if "PASSED" in output else "0",
                "Failed validations": str(len(self._parse_validation(output))) if error or "FAILED" in output else "0",
            }
        )
        rows = "\n".join(
            f"<tr><th>{self._escape(key)}</th><td>{self._escape(value)}</td></tr>"
            for key, value in values.items()
        )
        html = (
            "<!doctype html><html><head><meta charset='utf-8'><title>FLEX execution summary</title>"
            "<style>body{font-family:Segoe UI,Arial;margin:24px}table{border-collapse:collapse;min-width:720px}"
            "th,td{border:1px solid #ccd;padding:8px;text-align:left}th{background:#eef}</style></head>"
            f"<body><h1>FLEX Execution Summary</h1><table>{rows}</table></body></html>"
        )
        allure.attach(html, "execution-summary.html", allure.attachment_type.HTML)

    def _attach_validation(self, output: str):
        fields = self._parse_validation(output)
        rows = "".join(
            "<tr>" + "".join(f"<td>{self._escape(value)}</td>" for value in row) + "</tr>"
            for row in fields
        )
        html = (
            "<!doctype html><html><head><meta charset='utf-8'><title>FLEX validation</title>"
            "<style>body{font-family:Segoe UI,Arial;margin:24px}table{border-collapse:collapse}"
            "th,td{border:1px solid #ccd;padding:8px}th{background:#eef}</style></head>"
            "<body><h1>Validation Report</h1><table><tr><th>Parameter</th><th>Expected</th>"
            "<th>Actual</th><th>Difference</th><th>Result</th></tr>"
            f"{rows}</table></body></html>"
        )
        allure.attach(html, "validation-report.html", allure.attachment_type.HTML)

    def _attach_environment(self, *, args, ended_at):
        text = self._environment_text(args=args, ended_at=ended_at)
        allure.attach(text, "environment.properties", allure.attachment_type.TEXT)
        if self.results_dir is not None:
            (self.results_dir / "environment.properties").write_text(text, encoding="utf-8")

    def _environment_text(self, *, args, ended_at):
        return "\n".join(
            [
                f"FW version={self._find_value('FW version') or 'unknown'}",
                "Controller type=FLEX",
                f"Device type={self._find_value('Device type') or 'unknown'}",
                f"Device name={self._find_value('Device name') or 'unknown'}",
                f"HW revision={self._find_value('HW Revision') or 'unknown'}",
                f"BSP version={self._find_value('BSP version') or 'unknown'}",
                f"Git commit={self._find_value('Git commit') or 'unknown'}",
                f"Build date={self._find_value('Build date') or 'unknown'}",
                f"Build={self._find_value('Build') or 'unknown'}",
                f"COM port={args.port}",
                f"Test machine={platform.node()} ({platform.platform()})",
                f"Python version={sys.version.split()[0]}",
                f"Execution timestamp={ended_at.astimezone().isoformat()}",
            ]
        )

    def _write_allure_metadata(self, *, args, ended_at):
        if self.results_dir is None:
            return
        self.results_dir.mkdir(parents=True, exist_ok=True)
        (self.results_dir / "categories.json").write_text(
            json.dumps(
                [
                    {"name": "Communication Failure", "matchedStatuses": ["broken"], "messageRegex": ".*(serial|com|connect).*"},
                    {"name": "Timeout Failure", "matchedStatuses": ["broken"], "messageRegex": ".*timeout.*"},
                    {"name": "Validation Failure", "matchedStatuses": ["failed"], "messageRegex": ".*(validation|expected|actual).*"},
                    {"name": "Configuration Failure", "matchedStatuses": ["broken"], "messageRegex": ".*(config|recipe|program).*"},
                    {"name": "Unexpected Exception", "matchedStatuses": ["broken"]},
                ],
                indent=2,
            ),
            encoding="utf-8",
        )

    def rich_title(self, output: str) -> str:
        scenario = self._last_value(output, "Scenario") or "FLEX Hardware Run"
        program_id = self._last_value(output, "Program ID") or "?"
        dosing_match = re.findall(
            r"Plan amount:\s*([^,]+),\s*Method:\s*([^,]+),\s*Units:\s*([^,]+)",
            output,
            re.IGNORECASE,
        )
        if dosing_match:
            amount, method, units = dosing_match[-1]
            dosing_text = f"{method.strip()} {units.strip()} {amount.strip()}"
        else:
            dosing_text = "Controller"
        firmware = self._last_value(output, "FW version") or "unknown"
        return f"Program {program_id} | {scenario} | {dosing_text} | FW {firmware}"

    def _attach_session_files(self, session_dir: Path | None):
        if session_dir is None or not session_dir.exists():
            return
        for path in sorted(session_dir.rglob("*")):
            if path.is_file():
                attachment_type = self._attachment_type(path)
                allure.attach.file(str(path), name=f"session/{path.name}", attachment_type=attachment_type)

    @staticmethod
    def _attachment_type(path: Path):
        suffix = path.suffix.lower()
        return {
            ".json": allure.attachment_type.JSON,
            ".csv": allure.attachment_type.CSV,
            ".html": allure.attachment_type.HTML,
            ".png": allure.attachment_type.PNG,
            ".jpg": allure.attachment_type.JPG,
            ".jpeg": allure.attachment_type.JPG,
        }.get(suffix, allure.attachment_type.TEXT)

    @staticmethod
    def _parse_summary(output: str) -> dict[str, str]:
        keys = (
            "Program ID", "Program Type", "Expected Water", "Actual Water",
            "Expected Dose", "Actual Dose", "PASS / FAIL", "Firmware version",
        )
        result = {}
        for key in keys:
            match = re.search(rf"^{re.escape(key)}\s*:\s*(.+)$", output, re.MULTILINE)
            if match:
                result[key] = match.group(1).strip()
        return result

    @staticmethod
    def _first_value(output: str, key: str):
        match = re.search(rf"^{re.escape(key)}\s*:\s*(.+)$", output, re.MULTILINE)
        return match.group(1).strip() if match else None

    @staticmethod
    def _last_value(output: str, key: str):
        matches = re.findall(rf"^{re.escape(key)}\s*:\s*(.+)$", output, re.MULTILINE)
        return matches[-1].strip() if matches else None

    @staticmethod
    def _parse_validation(output: str):
        result = []
        match = re.search(r"Expected Water\s*:\s*(.+).*?Actual Water\s*:\s*(.+).*?Expected Dose\s*:\s*(.+).*?Actual Dose\s*:\s*(.+)", output, re.DOTALL)
        if match:
            for name, expected, actual in (
                ("Water", match.group(1), match.group(2)),
                ("Dosing", match.group(3), match.group(4)),
            ):
                result.append((name, expected.strip(), actual.strip(), "see scenario tolerance", "PASS" if "PASSED" in output else "FAIL"))
        return result

    @staticmethod
    def _section_excerpt(output: str, marker: str | None) -> str:
        if not marker:
            return output[-4000:]
        index = output.lower().find(marker.lower())
        return output[index:index + 4000] if index >= 0 else ""

    @staticmethod
    def _escape(value) -> str:
        return (
            str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )

    @staticmethod
    def failure_category(error) -> str:
        message = str(error).lower()
        if "timeout" in message:
            return "Timeout Failure"
        if any(token in message for token in ("serial", "com", "connect")):
            return "Communication Failure"
        if any(token in message for token in ("validation", "expected", "actual")):
            return "Validation Failure"
        if any(token in message for token in ("config", "recipe", "program")):
            return "Configuration Failure"
        return "Unexpected Exception"

    def _attach_text(self, name: str, content: str):
        allure.attach(content or "", name=name, attachment_type=allure.attachment_type.TEXT)

    def _find_value(self, key: str):
        match = re.search(rf"^{re.escape(key)}\s*:\s*(.+)$", self.console.getvalue(), re.MULTILINE)
        return match.group(1).strip() if match else None