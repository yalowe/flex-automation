import os
import subprocess

from services.flex_gui_service import FlexGuiSession
from services.analyzer_policy import resolve_policy
from services.expectation_builder import ExpectationBuilder
from services.report_parser import ReportParser
from runner.programs_and_dosings_parsing import (
    estimate_timeout_sec,
    extract_active_program_state,
    extract_report_shift_id,
)
from runner.programs_and_dosings_output import (
    print_dosing_diagnostics,
    print_monitoring_summary,
    print_scenario_summary,
)
from runner.programs_and_dosings_monitoring import assert_monitoring_clean
from runner.programs_and_dosings_polling import (
    wait_for_completed_report,
    wait_for_current_run_start_time,
)
from runner.programs_and_dosings_runtime import stop_running_program
from runner.programs_and_dosings_validation import (
    validate_results_from_controller,
)


def _resolve_analyzer_policy_for_program(program_id: int) -> str:
    mapping_text = os.getenv("FLEX_HEADLESS_ANALYZER_POLICY_MAP", "")
    default_policy = os.getenv("FLEX_HEADLESS_ANALYZER_DEFAULT_POLICY", "safe")
    return resolve_policy(mapping_text, default_policy, program_id)


def _run_headless_analyzer_hook(
    *,
    scenario_name: str,
    program_id: int,
    session_dir: str,
    anomaly_count: int,
) -> tuple[bool, str]:
    """Run optional post-scenario analyzer command from environment.

    Expected environment variables:
    - FLEX_HEADLESS_ANALYZER_CMD: command template to run (disabled when empty)
    - FLEX_HEADLESS_ANALYZER_STRICT: when true, non-zero exit fails scenario

    Template placeholders:
    - {scenario_name}
    - {program_id}
    - {session_dir}
    - {anomaly_count}
    """

    cmd_template = os.getenv("FLEX_HEADLESS_ANALYZER_CMD", "").strip()
    if not cmd_template:
        return True, ""

    cmd = cmd_template.format(
        scenario_name=scenario_name,
        program_id=program_id,
        session_dir=session_dir,
        anomaly_count=anomaly_count,
        policy=_resolve_analyzer_policy_for_program(program_id),
    )

    print(f"Running headless analyzer hook: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())

    if result.returncode != 0:
        return False, (
            "Headless analyzer hook failed " f"(exit_code={result.returncode})"
        )

    return True, ""


class ProgramsAndDosings:

    def __init__(
        self,
        irrigation,
        config,
        fail_on_anomalies=False,
        anomaly_blocklist=None,
        flex_gui_session: FlexGuiSession | None = None,
    ):

        self.irrigation = irrigation
        self.config = config
        self.fail_on_anomalies = fail_on_anomalies
        self.flex_gui_session = flex_gui_session
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

        # print("\n========== PROGRAMS INFO ==========")
        programs_info = self.irrigation.programs_info().response
        # print(programs_info)

        active_program_id, active_program_state = extract_active_program_state(
            programs_info
        )

        # print("\n========== SHIFTS INFO ==========")
        # print(self.irrigation.shifts_info().response)

        # print("\n========== RECIPES INFO ==========")
        # print(self.irrigation.recipes_info().response)

        # print("\n==================================\n")

        if active_program_state == "Running":
            stop_running_program(
                irrigation=self.irrigation,
                active_program_id=active_program_id,
                target_program_id=scenario.program_id,
            )

        result = self.irrigation.run_program(scenario.program_id)

        assert result.success, result.response

        current_run_start_time = wait_for_current_run_start_time(
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

        timeout_sec = estimate_timeout_sec(
            config_data=config_data,
            fallback_wait_sec=getattr(scenario, "wait_time_sec", None),
            program_units=config_data.get("program_units"),
            shift_amount=config_data.get("shift_amount", 0),
            water_before=config_data.get("water_before", 0),
            water_after=config_data.get("water_after", 0),
            flow=config_data.get("flow", 0.0),
        )

        print(f"Waiting for completed report (timeout={timeout_sec}s)...")

        completed_report = wait_for_completed_report(
            irrigation=self.irrigation,
            program_id=scenario.program_id,
            timeout_sec=timeout_sec,
            expected_start_time=current_run_start_time,
        )

        print(completed_report)

        print(
            "Actual Start Time:", ReportParser.parse_actual_start_time(completed_report)
        )

        print("================================\n")

        finish_reason = ReportParser.parse_finish_reason(completed_report)

        report_shift_id = extract_report_shift_id(completed_report)

        assert finish_reason in {"Completed", "Stopped"}, (
            f"Expected finish reason in Completed/Stopped " f"but got '{finish_reason}'"
        )

        data = ReportParser.parse_completed_report(completed_report)

        actual_dosing_channels = ReportParser.parse_dosing_channels(completed_report)

        print("\n========== RESULTS ==========")
        print(f"Water Delivered  : {data['water_delivered']}")
        print(f"Water Time       : {data['water_time']}")
        print(f"Dosing Delivered : {data['dosing_delivered']}")
        print(f"Dosing Time      : {data['dosing_time']}")
        print(f"Dosing Remaining : {data['dosing_remaining']}")
        print("=============================\n")

        print_dosing_diagnostics(
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
                print_monitoring_summary(summary)

        if summary is not None and self.fail_on_anomalies:
            try:
                assert_monitoring_clean(summary, self.anomaly_blocklist)
            except Exception as ex:
                if scenario_error is None:
                    scenario_error = ex

        if summary is not None:
            hook_ok, hook_error = _run_headless_analyzer_hook(
                scenario_name=scenario.name,
                program_id=scenario.program_id,
                session_dir=str(getattr(monitoring, "session_dir", "")),
                anomaly_count=summary.get("anomaly_count", 0),
            )
            hook_strict = os.getenv(
                "FLEX_HEADLESS_ANALYZER_STRICT", ""
            ).strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
            if not hook_ok and hook_strict and scenario_error is None:
                scenario_error = RuntimeError(hook_error)

        scenario_passed = scenario_error is None

        print_scenario_summary(
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

    def close(self) -> None:
        if self.flex_gui_session is not None:
            self.flex_gui_session.close()
