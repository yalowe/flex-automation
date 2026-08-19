import math
import re
import time

from services.flex_gui_service import FlexGuiSession
from services.expectation_builder import ExpectationBuilder
from flex.response_parser import FlexResponseParser
from runner.programs_and_dosings_validation import (
    validate_results_from_controller,
)


BLOCKED_ANOMALIES = {
    "command_error",
    "battery_recovery_state",
    "flow_alarm_pattern",
}


def _assert_monitoring_clean(summary: dict) -> None:
    blocked = [
        (anomaly_type, line)
        for _, _, anomaly_type, line in summary["anomalies"]
        if anomaly_type in BLOCKED_ANOMALIES
    ]

    if not blocked:
        return

    details = "\n".join(
        f"- {anomaly_type}: {line}" for anomaly_type, line in blocked[:10]
    )
    raise AssertionError("Blocked monitoring anomalies detected:\n" f"{details}")


def _wait_until_program_not_running(
    irrigation,
    timeout_sec=120,
    poll_sec=2,
    raise_on_timeout=True,
):
    timeout = time.time() + timeout_sec

    while time.time() < timeout:
        programs_info = irrigation.programs_info().response
        _, active_program_state = _extract_active_program_state(programs_info)

        if active_program_state != "Running":
            print(
                "Controller is no longer in Running state. "
                "Starting target program..."
            )
            return True

        time.sleep(poll_sec)

    if raise_on_timeout:
        raise TimeoutError("Timeout waiting for controller to leave Running state")

    return False


def _skip_all_running_shifts(
    irrigation,
    fallback_program_id,
    max_shift_skips=20,
    poll_sec=2,
):
    for skip_index in range(max_shift_skips):
        programs_info = irrigation.programs_info().response
        active_program_id, active_program_state = _extract_active_program_state(
            programs_info
        )

        if active_program_state != "Running":
            print(
                "Controller is no longer in Running state. "
                "Starting target program..."
            )
            return

        running_program_id = (
            active_program_id if active_program_id is not None else fallback_program_id
        )
        print(f"Skipping shift #{skip_index + 1} for Program {running_program_id}...")

        skip_shift_result = irrigation.skip_shift(running_program_id)
        assert skip_shift_result.success, (
            "Failed to skip running shift before restart. "
            f"Response: {skip_shift_result.response}"
        )

        if _wait_until_program_not_running(
            irrigation=irrigation,
            timeout_sec=10,
            poll_sec=poll_sec,
            raise_on_timeout=False,
        ):
            return

    raise TimeoutError("Timeout while skipping all running shifts before restart")


def _stop_running_program(irrigation, active_program_id, target_program_id):
    running_program_id = (
        active_program_id if active_program_id is not None else target_program_id
    )
    print(
        "Detected running program. "
        f"Skipping Program {running_program_id} before restart..."
    )

    skip_program_result = irrigation.skip_program(running_program_id)
    assert skip_program_result.success, (
        "Failed to skip running program before restart. "
        f"Response: {skip_program_result.response}"
    )

    if _wait_until_program_not_running(
        irrigation=irrigation,
        timeout_sec=20,
        poll_sec=2,
        raise_on_timeout=False,
    ):
        return

    print(
        "Program is still running after skip program command. "
        "Skipping remaining shifts..."
    )
    _skip_all_running_shifts(
        irrigation=irrigation,
        fallback_program_id=running_program_id,
        max_shift_skips=20,
        poll_sec=2,
    )


def _start_times_match(expected_start_time: str, report_start_time: str) -> bool:
    if expected_start_time == report_start_time:
        return True

    expected_parts = expected_start_time.split(":")
    report_parts = report_start_time.split(":")
    if len(expected_parts) >= 2 and len(report_parts) >= 2:
        return expected_parts[:2] == report_parts[:2]

    return False


def _report_state_is_running(report_text: str) -> bool:
    match = re.search(r"Program Id:\s*(\d+).*?State:\s*(\w+)", report_text)
    if not match:
        return False

    program_id, state = match.groups()
    print(f"Program ID: {program_id.strip()}, State: {state.strip()}")
    return state.strip().lower() == "running"


def _extract_program_units(programs_info: str, program_id: int):
    for line in programs_info.splitlines():
        row_match = re.match(r"\s*(\d+)\|", line)
        if not row_match or int(row_match.group(1)) != program_id:
            continue

        parts = [part.strip() for part in line.split("|")]
        if len(parts) > 5:
            return parts[5]

    return None


def _estimate_timeout_sec(
    config_data: dict | None = None,
    fallback_wait_sec: int | None = None,
    program_units=None,
    shift_amount: int = 0,
    water_before: int = 0,
    water_after: int = 0,
    flow: float = 0.0,
) -> int:
    if config_data is not None:
        program_units = config_data.get("program_units", program_units)
        shift_amount = config_data.get("shift_amount", shift_amount)
        water_before = config_data.get("water_before", water_before)
        water_after = config_data.get("water_after", water_after)
        flow = config_data.get("flow", flow)

    fallback_wait_sec = fallback_wait_sec if fallback_wait_sec is not None else 600
    default_timeout = max(fallback_wait_sec + 300, 600)
    if not program_units:
        return default_timeout

    normalized_units = str(program_units).strip().lower()
    if normalized_units == "time" and shift_amount > 0:
        runtime_sec = (shift_amount * 60) + ((water_before + water_after) * 60)
        return max(runtime_sec + 300, default_timeout)

    if shift_amount <= 0:
        return default_timeout

    effective_flow_lph = max(float(flow) * 1000.0, 0.0)
    if effective_flow_lph <= 0:
        return default_timeout

    planned_liters = shift_amount / 100.0
    runtime_sec = (planned_liters / effective_flow_lph) * 3600.0
    runtime_sec += (water_before + water_after) * 60
    if normalized_units in {
        "quantity",
        "qty",
        "quant",
        "depth",
        "mm",
        "millimeter",
        "millimeters",
    }:
        return max(int(math.ceil(runtime_sec + 300)), default_timeout)

    return default_timeout


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


def _extract_report_shift_id(report_text: str):
    match = re.search(r"Shift Id:\s*(\d+)", report_text)
    return int(match.group(1)) if match else None


def _configured_expected_dose(config_data: dict):
    amounts = [
        channel.get("amount")
        for channel in config_data.get("dosing_channels", {}).values()
        if channel.get("enabled") and channel.get("amount") is not None
    ]
    return sum(amounts) if amounts else None


def _wait_for_current_run_start_time(
    irrigation,
    program_id,
    timeout_sec=60,
    poll_sec=2,
):
    timeout = time.time() + timeout_sec

    while time.time() < timeout:
        report = irrigation.running_report(program_id)
        if "Report type: Running" not in report.response:
            time.sleep(poll_sec)
            continue

        actual_start = FlexResponseParser.parse_actual_start_time(report.response)
        if actual_start:
            return actual_start

        time.sleep(poll_sec)

    return None


def _wait_for_completed_report(
    irrigation,
    program_id,
    timeout_sec=60,
    expected_start_time=None,
):
    timeout = time.time() + timeout_sec
    latest_finalized_report = None
    finalized_mismatch_count = 0
    active_program_state = None
    stale_report_logged = False
    last_live_snapshot = None

    while time.time() < timeout:
        programs_info = irrigation.programs_info().response
        _, active_program_state = _extract_active_program_state(programs_info)
        running_report = irrigation.running_report(program_id)
        live = FlexResponseParser.parse_live_report(running_report.response)
        live_rows = []
        for channel_id, channel in sorted(live["dosing_channels"].items()):
            delivered_time = channel["delivered_time"]
            flow_lph = channel["flow"] / 100
            dose_by_flow = flow_lph * delivered_time / 3600 * 100
            live_rows.append(
                (
                    channel_id,
                    channel["flow"],
                    delivered_time,
                    channel["delivered_quantity"],
                    round(dose_by_flow, 1),
                )
            )
        live_snapshot = (
            live["irrigation_flow_raw"],
            live["water_delivered"],
            live["water_time"],
            tuple(live_rows),
        )
        if live_snapshot != last_live_snapshot and live["irrigation_flow_raw"] is not None:
            print(
                "LIVE FLOW | "
                f"irrigation_raw={live['irrigation_flow_raw']} "
                f"water={live['water_delivered']} units "
                f"water_time={live['water_time']}s"
            )
            for channel_id, flow_raw, delivered_time, delivered_quantity, dose_by_flow in live_rows:
                print(
                    "LIVE DOSE | "
                    f"CH{channel_id} flow_raw={flow_raw} "
                    f"flow_assumed_lph={flow_raw / 100:.2f} "
                    f"time={delivered_time}s "
                    f"dose_by_live_flow={dose_by_flow} units "
                    f"dose_reported={delivered_quantity} units"
                )
            last_live_snapshot = live_snapshot

        report = irrigation.completed_report(program_id)

        if "Report type: Completed" not in report.response:
            time.sleep(5)
            continue

        completed_report = FlexResponseParser.extract_completed_report(report.response)
        try:
            finish_reason = FlexResponseParser.parse_finish_reason(completed_report)
        except ValueError:
            time.sleep(5)
            continue

        is_finalized = finish_reason in {"Completed", "Stopped"}
        report_start_time = FlexResponseParser.parse_actual_start_time(completed_report)
        if is_finalized:
            latest_finalized_report = completed_report

        if (
            expected_start_time
            and report_start_time
            and not _start_times_match(expected_start_time, report_start_time)
        ):
            if not stale_report_logged:
                print(
                    "Ignoring stale completed report. "
                    f"Expected start {expected_start_time}, got {report_start_time}."
                )
                stale_report_logged = True

            if is_finalized:
                finalized_mismatch_count += 1

            time.sleep(5)
            continue

        is_running_state = _report_state_is_running(completed_report)
        if is_running_state and finish_reason not in {"Completed", "Stopped"}:
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

    raise TimeoutError("Completed report did not stabilize")


def _expected_dose_formula_text(channel, expected, config_data, expectations):
    method = (channel.get("method") or "").strip().lower()
    units = (channel.get("units") or "").strip().lower()
    program_units = (config_data.get("program_units") or "").strip().lower()

    if method == "bulk" and units == "time":
        configured_runtime_minutes = float(channel.get("amount") or 0)
        effective_runtime_minutes = expectations.get("dosing_window_minutes")
        if program_units == "time" or effective_runtime_minutes is None:
            return (
                f"{channel.get('flow')} L/h x "
                f"({configured_runtime_minutes:g} min / 60) x 100"
            )
        return (
            f"{channel.get('flow')} L/h x "
            f"(min({configured_runtime_minutes:g}, {effective_runtime_minutes:g}) min / 60) x 100"
        )

    if method == "bulk" and units == "quant":
        return "configured quantity from recipe"

    if method in {"prop", "proportional"}:
        return (
            f"({expectations.get('expected_water_liters')} L / 1000) x "
            f"{expected.get('ratio_l_per_m3')} L/m3 x 1000"
        )

    if method == "spread" and units == "time":
        delivered_time_seconds = expected.get("spread_schedule", {}).get(
            "delivered_time_seconds"
        )
        return (
            f"{channel.get('flow')} L/h x ({delivered_time_seconds} sec / 3600) x 100"
        )

    return "unsupported or unresolved from current controller inputs"


def _print_dosing_diagnostics(config_data, expectations, actual_dosing_channels):
    active_channels = config_data.get("dosing_channels", {})
    channel_expectations = expectations.get("channel_expectations", {})
    if not active_channels:
        return

    print("========== DOSING DIAGNOSTICS ==========")
    for channel_id, channel in sorted(active_channels.items()):
        expected = channel_expectations.get(channel_id, {})
        actual = actual_dosing_channels.get(channel_id, {})
        actual_delivered = actual.get("delivered_quantity")
        actual_remaining = actual.get("remain_quantity")
        actual_total = (
            actual_delivered + actual_remaining
            if actual_delivered is not None and actual_remaining is not None
            else None
        )
        expected_result = expected.get("expected_report_units")
        difference = (
            actual_total - expected_result
            if expected_result is not None and actual_total is not None
            else None
        )

        print(f"Channel ID              : {channel_id}")
        print(f"DM ID                   : {channel_id}")
        print(f"Configured Dosing Flow  : {channel.get('flow')}")
        print(f"Configured Method       : {channel.get('method')}")
        print(f"Configured Ratio        : {expected.get('ratio_l_per_m3')}")
        print(f"DM Rate                 : {channel.get('dm_rate')}")
        print(
            "Derived DM Pulse Size    : "
            f"{expected.get('dm_pulse_size_liters', 'unknown')}"
        )
        print(
            "Expected Dose Formula    : "
            f"{_expected_dose_formula_text(channel, expected, config_data, expectations)}"
        )
        print(f"Expected Dose Result    : {expected_result}")
        print(f"Actual Delivered Dose   : {actual_delivered}")
        print(f"Actual Remaining Dose   : {actual_remaining}")
        print(f"Difference              : {difference}")
        print("---------------------------------------")

    print("=======================================\n")


def _print_scenario_summary(
    scenario,
    config_data,
    expectations,
    data,
    finish_reason,
    monitoring_summary,
    shift_id,
    passed,
):
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
    print(f"Expected Water  : {expectations.get('expected_water_report_units')}")
    print(f"Actual Water    : {data['water_delivered']}")
    print(f"Expected Dose   : {expectations.get('expected_dosing_report_units')}")
    print(f"Actual Dose     : {data['dosing_delivered']}")
    print(f"WM Cycle (ms)   : {config_data.get('wm_cycle')}")
    print("DM Cycle (ms)   : " f"{', '.join(dm_cycles) if dm_cycles else 'none'}")
    print(f"Finish Reason   : {finish_reason}")
    print(f"Anomaly Count   : {anomaly_count}")
    print(f"PASS / FAIL     : {'PASS' if passed else 'FAIL'}")
    print("======================================\n")


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
        for timestamp, command, anomaly_type, line in summary["anomalies"][:5]:
            print(f"- [{timestamp}] ({command}) {anomaly_type} | {line}")

    print("========================================\n")


class ProgramsAndDosings:

    def __init__(
        self,
        irrigation,
        config,
        flex_gui_session: FlexGuiSession | None = None,
    ):

        self.irrigation = irrigation
        self.config = config
        self.flex_gui_session = flex_gui_session

    def run_scenario(self, scenario):

        monitoring = getattr(self.irrigation.controller, "monitoring_service", None)

        marker = None
        if monitoring is not None:
            marker = monitoring.mark()

        config_data = self.config.get_program_configuration(scenario.program_id)

        if self.flex_gui_session is not None:
            self.flex_gui_session.prepare_for_program(config_data)

        print("========== PROGRAM CONFIG ==========")
        print(config_data)
        print("====================================")

        expectations = ExpectationBuilder.build(config_data)

        print("\n========== EXPECTATIONS ==========")
        print(expectations)
        print("==================================")

        programs_info = self.irrigation.programs_info().response

        active_program_id, active_program_state = _extract_active_program_state(
            programs_info
        )

        if active_program_state == "Running":
            _stop_running_program(
                irrigation=self.irrigation,
                active_program_id=active_program_id,
                target_program_id=scenario.program_id,
            )

        result = self.irrigation.run_program(scenario.program_id)

        assert result.success, result.response

        current_run_start_time = _wait_for_current_run_start_time(
            irrigation=self.irrigation,
            program_id=scenario.program_id,
            timeout_sec=60,
            poll_sec=2,
        )

        if current_run_start_time:
            print("Current run start marker: " f"{current_run_start_time}")
        else:
            print(
                "Warning: could not read current run start marker from running report. "
                "Completed report filtering will be less strict."
            )

        timeout_sec = _estimate_timeout_sec(
            config_data=config_data,
            fallback_wait_sec=getattr(scenario, "wait_time_sec", None),
            program_units=config_data.get("program_units"),
            shift_amount=config_data.get("shift_amount", 0),
            water_before=config_data.get("water_before", 0),
            water_after=config_data.get("water_after", 0),
            flow=config_data.get("flow", 0.0),
        )

        print(f"Waiting for completed report (timeout={timeout_sec}s)...")

        completed_report = _wait_for_completed_report(
            irrigation=self.irrigation,
            program_id=scenario.program_id,
            timeout_sec=timeout_sec,
            expected_start_time=current_run_start_time,
        )

        print(completed_report)

        print(
            "Actual Start Time:",
            FlexResponseParser.parse_actual_start_time(completed_report),
        )

        print("================================\n")

        finish_reason = FlexResponseParser.parse_finish_reason(completed_report)

        report_shift_id = _extract_report_shift_id(completed_report)

        assert finish_reason in {"Completed", "Stopped"}, (
            f"Expected finish reason in Completed/Stopped " f"but got '{finish_reason}'"
        )

        data = FlexResponseParser.parse_completed_report(completed_report)

        actual_dosing_channels = data["dosing_channels"]

        print("\n========== RESULTS ==========")
        print(f"Water Delivered  : {data['water_delivered']}")
        print(f"Water Time       : {data['water_time']}")
        print(f"Dosing Delivered : {data['dosing_delivered']}")
        print(f"Dosing Time      : {data['dosing_time']}")
        print(f"Dosing Remaining : {data['dosing_remaining']}")
        print("=============================\n")

        _print_dosing_diagnostics(
            config_data=config_data,
            expectations=expectations,
            actual_dosing_channels=actual_dosing_channels,
        )

        summary = None
        scenario_error = None

        try:
            validate_results_from_controller(
                config_data,
                expectations,
                data,
                scenario,
                actual_dosing_channels=actual_dosing_channels,
            )

            print(f"Scenario name: {scenario.name} PASSED (validation)")

        except Exception as ex:
            scenario_error = ex

        finally:
            if monitoring is not None and marker is not None:
                summary = monitoring.summarize_since(
                    marker,
                    scenario.name,
                )
                _print_monitoring_summary(summary)

        if summary is not None:
            try:
                _assert_monitoring_clean(summary)
            except Exception as ex:
                if scenario_error is None:
                    scenario_error = ex

        scenario_passed = scenario_error is None

        _print_scenario_summary(
            scenario=scenario,
            config_data=config_data,
            expectations=expectations,
            data=data,
            finish_reason=finish_reason,
            monitoring_summary=summary,
            shift_id=report_shift_id,
            passed=scenario_passed,
        )

        if scenario_error is not None:
            raise scenario_error

    def run_all(self, scenarios, run_count: int = 1) -> None:
        run_number = max(0, run_count)
        stats = {scenario.name: {"pass": 0, "fail": 0} for scenario in scenarios}

        while run_number > 0:
            print("=" * 100)

            for scenario in scenarios:
                print("-" * 100)
                print(
                    f"RUNNING: {scenario.name} " f"(Program ID {scenario.program_id})"
                )
                print("-" * 100)

                try:
                    self.run_scenario(scenario)
                    stats[scenario.name]["pass"] += 1
                    print(
                        f"PASSED: {scenario.name} "
                        f"(Program ID {scenario.program_id})"
                    )
                except Exception as ex:
                    stats[scenario.name]["fail"] += 1
                    print(
                        f"FAILED: {scenario.name} "
                        f"(Program ID {scenario.program_id})"
                    )
                    print(ex)

                time.sleep(10)

            self._print_summary(stats)
            run_number -= 1

    @staticmethod
    def _print_summary(stats) -> None:
        print("\n")
        print("=" * 100)
        print("CURRENT SUMMARY")
        print("=" * 100)

        for scenario_name, result in stats.items():
            print(
                f"{scenario_name:<35} : "
                f"{result['pass']} PASS | "
                f"{result['fail']} FAIL"
            )

        print("=" * 100)

    def close(self) -> None:
        if self.flex_gui_session is not None:
            self.flex_gui_session.close()
