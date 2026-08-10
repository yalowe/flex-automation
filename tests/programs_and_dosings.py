import time
import re

from services.expectation_builder import ExpectationBuilder
from services.report_parser import ReportParser


class ProgramsAndDosings:

    def __init__(
        self,
        irrigation,
        config,
        fail_on_anomalies=False,
        anomaly_blocklist=None,
    ):
        self.irrigation = irrigation
        self.config = config
        self.fail_on_anomalies = fail_on_anomalies
        self.anomaly_blocklist = set(
            anomaly_blocklist
            if anomaly_blocklist is not None
            else [
                "command_error",
                "battery_recovery_state",
                "flow_alarm_pattern",
            ]
        )

    def run_scenario(self, scenario):

        monitoring = getattr(
            self.irrigation.controller,
            "monitoring_service",
            None,
        )

        marker = None
        if monitoring is not None:
            marker = monitoring.mark()

        print(f"\n?? {scenario.name}")

        config_data = self.config.get_program_configuration(
            scenario.program_id
        )

        print()
        print("========== PROGRAM CONFIG ==========")
        print(config_data)
        print("====================================")

        expectations = ExpectationBuilder.build(config_data)

        print("\n========== EXPECTATIONS ==========")
        print(expectations)
        print("==================================")

        print("\n========== PROGRAMS INFO ==========")
        programs_info = self.irrigation.programs_info().response
        print(programs_info)

        active_program_id, active_program_state = self._extract_active_program_state(
            programs_info
        )

        print("\n========== SHIFTS INFO ==========")
        print(self.irrigation.shifts_info().response)

        print("\n========== RECIPES INFO ==========")
        print(self.irrigation.recipes_info().response)

        print("\n==================================\n")

        if active_program_state == "Running":
            self._stop_running_program(
                active_program_id=active_program_id,
                target_program_id=scenario.program_id,
            )

        result = self.irrigation.run_program(
            scenario.program_id
        )

        assert result.success, result.response

        current_run_start_time = self._wait_for_current_run_start_time(
            scenario.program_id,
            timeout_sec=60,
            poll_sec=2,
        )

        if current_run_start_time:
            print(
                "Current run start marker: "
                f"{current_run_start_time}"
            )
        else:
            print(
                "Warning: could not read current run start marker from running report. "
                "Completed report filtering will be less strict."
            )

        timeout_sec = self._estimate_timeout_sec(
            fallback_wait_sec=scenario.wait_time_sec,
            program_units=config_data.get("program_units"),
            shift_amount=config_data.get("shift_amount", 0),
        )

        print(
            f"Waiting for completed report (timeout={timeout_sec}s)..."
        )

        print("\n========== RAW REPORT ==========")

        completed_report = self.wait_for_completed_report(
            scenario.program_id,
            timeout_sec=timeout_sec,
            expected_start_time=current_run_start_time,
        )

        print(completed_report)

        print(
            "Actual Start Time:",
            ReportParser.parse_actual_start_time(
                completed_report
            )
        )

        print("================================\n")

        finish_reason = (
            ReportParser.parse_finish_reason(
                completed_report
            )
        )

        report_shift_id = self._extract_report_shift_id(
            completed_report
        )

        assert finish_reason in {"Completed", "Stopped"}, (
            f"Expected finish reason in Completed/Stopped "
            f"but got '{finish_reason}'"
        )

        data = (
            ReportParser.parse_completed_report(
                completed_report
            )
        )

        actual_dosing_channels = (
            ReportParser.parse_dosing_channels(
                completed_report
            )
        )

        print("\n========== RESULTS ==========")
        print(f"Water Delivered  : {data['water_delivered']}")
        print(f"Water Time       : {data['water_time']}")
        print(f"Dosing Delivered : {data['dosing_delivered']}")
        print(f"Dosing Time      : {data['dosing_time']}")
        print(f"Dosing Remaining : {data['dosing_remaining']}")
        print("=============================\n")

        self._print_dosing_diagnostics(
            config_data=config_data,
            expectations=expectations,
            actual_dosing_channels=actual_dosing_channels,
        )

        summary = None

        try:
            self.validate_results_from_controller(
                config_data,
                expectations,
                data,
                scenario,
            )

            print(f"? {scenario.name} PASSED")

        finally:
            if monitoring is not None and marker is not None:
                summary = monitoring.summarize_since(
                    marker,
                    scenario.name,
                )
                self._print_monitoring_summary(summary)

        self._print_scenario_summary(
            scenario=scenario,
            config_data=config_data,
            expectations=expectations,
            data=data,
            finish_reason=finish_reason,
            monitoring_summary=summary,
            shift_id=report_shift_id,
        )

        if summary is not None and self.fail_on_anomalies:
            self._assert_monitoring_clean(summary)

    @staticmethod
    def validate_results_from_controller(
        config_data,
        expectations,
        data,
        scenario=None,
    ):

        documented_issues = []

        if scenario is not None:
            documented_issues = (
                ExpectationBuilder.compare_documented_expectations(
                    expectations=expectations,
                    documented_water=scenario.expected_water,
                    documented_dosing=scenario.expected_dosing,
                )
            )

        for issue in expectations.get("inconsistencies", []):
            print(issue)

        for issue in documented_issues:
            print(issue)

        flow = config_data.get("flow", 0)

        expected_water = expectations.get("expected_water_report_units")
        expected_dosing = expectations.get("expected_dosing_report_units")
        expected_plan = expectations.get("expected_plan_report_units")

        if expected_water is not None:
            assert ProgramsAndDosings.verify_tolerance(
                actual=data["water_delivered"],
                expected=expected_water,
                tolerance_percent=10,
            ), (
                "Controller-driven validation failed: "
                f"water_delivered={data['water_delivered']} "
                f"expected={expected_water}"
            )
        elif flow > 0:
            assert data["water_delivered"] > 0, (
                "Controller-driven validation failed: "
                "water_delivered must be > 0 when flow > 0"
            )

        assert data["water_time"] >= 0, (
            "Controller-driven validation failed: "
            "water_time must be non-negative"
        )

        active_dosing_channels = config_data.get("dosing_channels", {})
        enabled_channels = [
            channel
            for channel in active_dosing_channels.values()
            if channel.get("enabled")
        ]

        if expected_plan is not None:
            actual_plan = (
                data["dosing_delivered"]
                + data["dosing_remaining"]
            )

            assert ProgramsAndDosings.verify_tolerance(
                actual=actual_plan,
                expected=expected_plan,
                tolerance_percent=15,
            ), (
                "Controller-driven validation failed: "
                f"dosing_plan={actual_plan} "
                f"expected={expected_plan}"
            )
        elif enabled_channels:
            total_dosing = (
                data["dosing_delivered"]
                + data["dosing_remaining"]
            )

            assert total_dosing > 0, (
                "Controller-driven validation failed: "
                "enabled dosing channels require dosing activity"
            )

        assert data["dosing_remaining"] >= 0, (
            "Controller-driven validation failed: "
            "dosing_remaining must be non-negative"
        )

    @staticmethod
    def verify_tolerance(
        actual,
        expected,
        tolerance_percent,
    ):

        delta = expected * tolerance_percent / 100

        return abs(actual - expected) <= delta

    def wait_for_completed_report(
        self,
        program_id,
        timeout_sec=60,
        expected_start_time=None,
    ):

        timeout = time.time() + timeout_sec
        latest_finalized_report = None
        finalized_mismatch_count = 0
        active_program_state = None

        while time.time() < timeout:

            programs_info = self.irrigation.programs_info().response
            _, active_program_state = self._extract_active_program_state(
                programs_info
            )

            report = self.irrigation.completed_report(
                program_id
            )

            if "Report type: Completed" not in report.response:
                time.sleep(5)
                continue

            completed_report = (
                ReportParser.extract_completed_report(
                    report.response
                )
            )

            try:
                ReportParser.parse_finish_reason(
                    completed_report
                )
            except ValueError:
                time.sleep(5)
                continue

            report_start_time = ReportParser.parse_actual_start_time(
                completed_report
            )

            if not self._report_state_is_running(
                completed_report
            ):
                latest_finalized_report = completed_report

            if (
                expected_start_time
                and report_start_time
                and not self._start_times_match(
                    expected_start_time,
                    report_start_time,
                )
            ):
                print(
                    "Ignoring stale completed report. "
                    f"Expected start {expected_start_time}, "
                    f"got {report_start_time}."
                )
                if not self._report_state_is_running(
                    completed_report
                ):
                    finalized_mismatch_count += 1
                time.sleep(5)
                continue

            if self._report_state_is_running(
                completed_report
            ):
                print(
                    "Ignoring completed report block with state Running. "
                    "Waiting for finalized report..."
                )
                time.sleep(5)
                continue

            return completed_report

        if (
            latest_finalized_report is not None
            and active_program_state != "Running"
            and finalized_mismatch_count >= 3
        ):
            print(
                "Controller is not running and finalized completed report "
                "exists, but start marker did not match exactly. "
                "Using latest finalized completed report."
            )
            return latest_finalized_report

        raise TimeoutError(
            "Completed report did not stabilize"
        )

    @staticmethod
    def _start_times_match(
        expected_start_time: str,
        report_start_time: str,
    ) -> bool:

        if expected_start_time == report_start_time:
            return True

        expected_parts = expected_start_time.split(":")
        report_parts = report_start_time.split(":")

        if len(expected_parts) >= 2 and len(report_parts) >= 2:
            expected_hm = ":".join(expected_parts[:2])
            report_hm = ":".join(report_parts[:2])
            if expected_hm == report_hm:
                return True

        return False

    def _wait_for_current_run_start_time(
        self,
        program_id,
        timeout_sec=60,
        poll_sec=2,
    ):

        timeout = time.time() + timeout_sec

        while time.time() < timeout:
            report = self.irrigation.running_report(
                program_id
            )

            if "Report type: Running" not in report.response:
                time.sleep(poll_sec)
                continue

            running_report = report.response
            actual_start = ReportParser.parse_actual_start_time(
                running_report
            )

            if actual_start:
                return actual_start

            time.sleep(poll_sec)

        return None

    @staticmethod
    def _report_state_is_running(report_text: str) -> bool:

        match = re.search(
            r"Program Id:\s*\d+.*?State:\s*(\w+)",
            report_text,
        )

        if not match:
            return False

        return match.group(1).strip().lower() == "running"

    @staticmethod
    def _extract_program_units(programs_info: str, program_id: int):

        for line in programs_info.splitlines():
            row_match = re.match(r"\s*(\d+)\|", line)

            if not row_match:
                continue

            if int(row_match.group(1)) != program_id:
                continue

            parts = [part.strip() for part in line.split("|")]

            if len(parts) > 5:
                return parts[5]

        return None

    @staticmethod
    def _estimate_timeout_sec(
        fallback_wait_sec: int,
        program_units,
        shift_amount: int,
    ) -> int:

        default_timeout = max(fallback_wait_sec + 300, 600)

        if not program_units:
            return default_timeout

        normalized_units = program_units.strip().lower()

        if normalized_units == "time" and shift_amount > 0:
            return max((shift_amount * 60) + 300, default_timeout)

        return default_timeout

    @staticmethod
    def _extract_active_program_state(programs_info: str):

        active_program_id = None
        active_program_state = None

        for line in programs_info.splitlines():
            if "ProgramID:" in line:
                match = re.search(r"ProgramID:\s*(\d+)", line)
                if match:
                    active_program_id = int(match.group(1))

            if "Program State:" in line:
                match = re.search(r"Program State:\s*(\w+)", line)
                if match:
                    active_program_state = match.group(1)

        return active_program_id, active_program_state

    def _stop_running_program(self, active_program_id, target_program_id):

        running_program_id = (
            active_program_id
            if active_program_id is not None
            else target_program_id
        )

        print(
            "Detected running program. "
            f"Skipping Program {running_program_id} before restart..."
        )

        skip_program_result = self.irrigation.skip_program(
            running_program_id
        )

        assert skip_program_result.success, (
            "Failed to skip running program before restart. "
            f"Response: {skip_program_result.response}"
        )

        if self._wait_until_program_not_running(
            timeout_sec=20,
            poll_sec=2,
            raise_on_timeout=False,
        ):
            return

        print(
            "Program is still running after skip program command. "
            "Skipping remaining shifts..."
        )

        self._skip_all_running_shifts(
            fallback_program_id=running_program_id,
            max_shift_skips=20,
            poll_sec=2,
        )

    def _skip_all_running_shifts(
        self,
        fallback_program_id,
        max_shift_skips=20,
        poll_sec=2,
    ):

        for skip_index in range(max_shift_skips):
            programs_info = self.irrigation.programs_info().response
            active_program_id, active_program_state = (
                self._extract_active_program_state(
                    programs_info
                )
            )

            if active_program_state != "Running":
                print(
                    "Controller is no longer in Running state. "
                    "Starting target program..."
                )
                return

            running_program_id = (
                active_program_id
                if active_program_id is not None
                else fallback_program_id
            )

            print(
                f"Skipping shift #{skip_index + 1} "
                f"for Program {running_program_id}..."
            )

            skip_shift_result = self.irrigation.skip_shift(
                running_program_id
            )

            assert skip_shift_result.success, (
                "Failed to skip running shift before restart. "
                f"Response: {skip_shift_result.response}"
            )

            if self._wait_until_program_not_running(
                timeout_sec=10,
                poll_sec=poll_sec,
                raise_on_timeout=False,
            ):
                return

        raise TimeoutError(
            "Timeout while skipping all running shifts before restart"
        )

    def _wait_until_program_not_running(
        self,
        timeout_sec=120,
        poll_sec=2,
        raise_on_timeout=True,
    ):

        timeout = time.time() + timeout_sec

        while time.time() < timeout:
            programs_info = self.irrigation.programs_info().response
            _, active_program_state = self._extract_active_program_state(
                programs_info
            )

            if active_program_state != "Running":
                print(
                    "Controller is no longer in Running state. "
                    "Starting target program..."
                )
                return True

            time.sleep(poll_sec)

        if raise_on_timeout:
            raise TimeoutError(
                "Timeout waiting for controller to leave Running state"
            )

        return False

    @staticmethod
    def _extract_report_shift_id(report_text: str):

        match = re.search(r"Shift Id:\s*(\d+)", report_text)

        if not match:
            return None

        return int(match.group(1))

    @staticmethod
    def _configured_expected_dose(config_data: dict):

        dosing_channels = config_data.get("dosing_channels", {})

        amounts = [
            channel.get("amount")
            for channel in dosing_channels.values()
            if channel.get("enabled") and channel.get("amount") is not None
        ]

        if not amounts:
            return None

        return sum(amounts)

    def _print_dosing_diagnostics(
        self,
        config_data,
        expectations,
        actual_dosing_channels,
    ):

        active_channels = config_data.get("dosing_channels", {})
        channel_expectations = expectations.get("channel_expectations", {})

        if not active_channels:
            return

        print("========== DOSING DIAGNOSTICS ==========")

        for channel_id, channel in sorted(active_channels.items()):
            expected = channel_expectations.get(channel_id, {})
            actual = actual_dosing_channels.get(channel_id, {})
            method = channel.get("method")
            units = channel.get("units")
            ratio = expected.get("ratio_l_per_m3")
            expected_result = expected.get("expected_report_units")
            actual_delivered = actual.get("delivered_quantity")
            actual_remaining = actual.get("remain_quantity")
            actual_total = None

            if actual_delivered is not None and actual_remaining is not None:
                actual_total = actual_delivered + actual_remaining

            difference = None
            if expected_result is not None and actual_total is not None:
                difference = actual_total - expected_result

            print(f"Channel ID              : {channel_id}")
            print(f"DM ID                   : {channel_id}")
            print(f"Configured Dosing Flow  : {channel.get('flow')}")
            print(f"Configured Method       : {method}")
            print(f"Configured Ratio        : {ratio}")
            print(f"DM Rate                 : {channel.get('dm_rate')}")
            print(
                "Derived DM Pulse Size    : "
                f"{expected.get('dm_pulse_size_liters', 'unknown')}"
            )
            print(
                "Expected Dose Formula    : "
                f"{self._expected_dose_formula_text(channel, expected, config_data, expectations)}"
            )
            print(f"Expected Dose Result    : {expected_result}")
            print(f"Actual Delivered Dose   : {actual_delivered}")
            print(f"Actual Remaining Dose   : {actual_remaining}")
            print(f"Difference              : {difference}")
            print("---------------------------------------")

        print("=======================================\n")

    @staticmethod
    def _expected_dose_formula_text(
        channel,
        expected,
        config_data,
        expectations,
    ):

        method = (channel.get("method") or "").strip().lower()
        units = (channel.get("units") or "").strip().lower()

        if method == "bulk" and units == "time":
            return (
                f"{channel.get('flow')} L/h x "
                f"({channel.get('amount')} min / 60) x 1000"
            )

        if method == "bulk" and units == "quant":
            return "configured quantity from recipe"

        if method in {"prop", "proportional"}:
            return (
                f"({expectations.get('expected_water_liters')} L / 1000) x "
                f"{expected.get('ratio_l_per_m3')} L/m3 x 1000"
            )

        if method == "spread" and units == "time":
            return (
                f"{channel.get('flow')} L/h x "
                f"({channel.get('amount')} min / 60) x 1000"
            )

        return "unsupported or unresolved from current controller inputs"

    def _print_scenario_summary(
        self,
        scenario,
        config_data,
        expectations,
        data,
        finish_reason,
        monitoring_summary,
        shift_id,
    ):

        expected_water = (
            expectations.get("expected_water_report_units")
        )

        expected_dose = (
            expectations.get("expected_dosing_report_units")
        )

        wm_cycle = config_data.get("wm_cycle")
        dm_cycles = [
            f"CH{channel_id}=DM{channel_id}:{channel.get('dm_cycle')}"
            for channel_id, channel in sorted(
                config_data.get("dosing_channels", {}).items()
            )
            if channel.get("enabled")
        ]

        anomaly_count = (
            monitoring_summary.get("anomaly_count", 0)
            if monitoring_summary is not None
            else 0
        )

        print("========== SCENARIO SUMMARY ==========")
        print(f"Scenario        : {scenario.name}")
        print(f"Program ID      : {config_data.get('program_id')}")
        print(f"Shift ID        : {shift_id or config_data.get('shift_id')}")
        print(f"Recipe ID       : {config_data.get('recipe_id')}")
        print(f"Expected Water  : {expected_water}")
        print(f"Actual Water    : {data['water_delivered']}")
        print(f"Expected Dose   : {expected_dose}")
        print(f"Actual Dose     : {data['dosing_delivered']}")
        print(f"WM Cycle (ms)   : {wm_cycle}")
        print(
            "DM Cycle (ms)   : "
            f"{', '.join(dm_cycles) if dm_cycles else 'none'}"
        )
        print(f"Finish Reason   : {finish_reason}")
        print(f"Anomaly Count   : {anomaly_count}")
        print(f"PASS / FAIL     : {'PASS'}")
        print("======================================\n")

    def _assert_monitoring_clean(self, summary: dict):

        blocked = []

        for anomaly in summary["anomalies"]:
            _, _, anomaly_type, line = anomaly

            if anomaly_type in self.anomaly_blocklist:
                blocked.append((anomaly_type, line))

        if not blocked:
            return

        details = "\n".join(
            f"- {anomaly_type}: {line}"
            for anomaly_type, line in blocked[:10]
        )

        raise AssertionError(
            "Blocked monitoring anomalies detected:\n"
            f"{details}"
        )

    @staticmethod
    def _print_monitoring_summary(summary: dict):

        print("\n========== MONITORING SUMMARY ==========")
        print(f"Scenario         : {summary['scenario']}")
        print(f"Captured Lines   : {summary['lines']}")
        print(f"Device Events    : {summary['device_events']}")
        print(f"Valve Opens      : {summary['valve_open_count']}")
        print(f"Valve Closes     : {summary['valve_close_count']}")
        print(f"WM Events        : {summary['wm_event_count']}")
        print(f"Anomalies        : {summary['anomaly_count']}")

        if summary["wm_last_counts"]:
            wm_text = ", ".join(
                f"WM{wm_id}={count}"
                for wm_id, count in sorted(summary["wm_last_counts"].items())
            )
            print(f"WM Last Counts   : {wm_text}")

        if summary["anomalies"]:
            print("Anomaly Samples  :")
            for anomaly in summary["anomalies"][:5]:
                timestamp, command, anomaly_type, line = anomaly
                print(
                    f"- [{timestamp}] ({command}) "
                    f"{anomaly_type} | {line}"
                )

        print("========================================\n")
