from services.expectation_builder import ExpectationBuilder
from services.report_parser import ReportParser
from tests.programs_and_dosings_parsing import (
    estimate_timeout_sec,
    extract_active_program_state,
    extract_report_shift_id,
)
from tests.programs_and_dosings_output import (
    print_dosing_diagnostics,
    print_monitoring_summary,
    print_scenario_summary,
)
from tests.programs_and_dosings_monitoring import assert_monitoring_clean
from tests.programs_and_dosings_polling import (
    wait_for_completed_report,
    wait_for_current_run_start_time,
)
from tests.programs_and_dosings_runtime import stop_running_program
from tests.programs_and_dosings_validation import (
    validate_results_from_controller,
)


class ProgramsAndDosings:

    def __init__(self, irrigation, config, fail_on_anomalies=False, anomaly_blocklist=None):

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

        monitoring = getattr(self.irrigation.controller, "monitoring_service",None)

        marker = None
        if monitoring is not None:
            marker = monitoring.mark()        

        config_data = self.config.get_program_configuration(scenario.program_id)

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

        active_program_id, active_program_state = extract_active_program_state(programs_info)

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
            print( "Current run start marker: " f"{current_run_start_time}")
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

        print("Actual Start Time:", ReportParser.parse_actual_start_time(completed_report))

        print("================================\n")

        finish_reason = ( ReportParser.parse_finish_reason(completed_report))

        report_shift_id = extract_report_shift_id(completed_report)

        assert finish_reason in {"Completed", "Stopped"}, (
            f"Expected finish reason in Completed/Stopped "
            f"but got '{finish_reason}'"
        )

        data = (ReportParser.parse_completed_report(completed_report))

        actual_dosing_channels = (ReportParser.parse_dosing_channels(completed_report))

        print("\n========== RESULTS ==========")
        print(f"Water Delivered  : {data['water_delivered']}")
        print(f"Water Time       : {data['water_time']}")
        print(f"Dosing Delivered : {data['dosing_delivered']}")
        print(f"Dosing Time      : {data['dosing_time']}")
        print(f"Dosing Remaining : {data['dosing_remaining']}")
        print("=============================\n")

        print_dosing_diagnostics(config_data=config_data, expectations=expectations, actual_dosing_channels=actual_dosing_channels)

        summary = None

        try:
            validate_results_from_controller(config_data, expectations, data, scenario)

            print(f"Scenario name: {scenario.name} PASSED")

        finally:
            if monitoring is not None and marker is not None:
                summary = monitoring.summarize_since(marker, scenario.name,)
                print_monitoring_summary(summary)

        print_scenario_summary(scenario=scenario, config_data=config_data, expectations=expectations, data=data, finish_reason=finish_reason,
            monitoring_summary=summary,
            shift_id=report_shift_id,
        )

        if summary is not None and self.fail_on_anomalies:
            assert_monitoring_clean(summary, self.anomaly_blocklist)

