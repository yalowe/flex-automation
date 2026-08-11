import time

from services.report_parser import ReportParser
from tests.programs_and_dosings_parsing import (
    extract_active_program_state,
    report_state_is_running,
    start_times_match,
)


def wait_for_current_run_start_time(
    irrigation,
    program_id,
    timeout_sec=60,
    poll_sec=2,
):

    timeout = time.time() + timeout_sec

    while time.time() < timeout:
        report = irrigation.running_report(
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


def wait_for_completed_report(
    irrigation,
    program_id,
    timeout_sec=60,
    expected_start_time=None,
):

    timeout = time.time() + timeout_sec
    latest_finalized_report = None
    finalized_mismatch_count = 0
    active_program_state = None

    while time.time() < timeout:

        programs_info = irrigation.programs_info().response
        _, active_program_state = extract_active_program_state(
            programs_info
        )

        report = irrigation.completed_report(
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

        print("\n[DEBUG][wait_for_completed_report] completed_report content:")
        print(completed_report)

        try:
            finish_reason = ReportParser.parse_finish_reason(
                completed_report
            )
        except ValueError:
            time.sleep(5)
            continue

        print("[DEBUG][wait_for_completed_report] finish_reason:")
        print(finish_reason)

        is_finalized = finish_reason in {"Completed", "Stopped"}

        report_start_time = ReportParser.parse_actual_start_time(
            completed_report
        )

        print("[DEBUG][wait_for_completed_report] report_start_time:")
        print(report_start_time)

        if is_finalized:
            latest_finalized_report = completed_report

        if (
            expected_start_time
            and report_start_time
            and not start_times_match(
                expected_start_time,
                report_start_time,
            )
        ):
            print(
                "Ignoring stale completed report. "
                f"Expected start {expected_start_time}, "
                f"got {report_start_time}."
            )
            if is_finalized:
                finalized_mismatch_count += 1
            time.sleep(5)
            continue

        is_running_state = report_state_is_running(
            completed_report
        )

        if is_running_state and finish_reason not in {"Completed", "Stopped"}:
            print(
                "Ignoring completed report block with state Running. "
                "Waiting for finalized report..."
            )
            time.sleep(5)
            continue

        if is_running_state and finish_reason in {"Completed", "Stopped"}:
            print(
                "[DEBUG][wait_for_completed_report] State is Running but finish reason is finalized; "
                "accepting completed report."
            )

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
