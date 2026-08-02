import time

from services.report_parser import ReportParser


class ProgramsAndDosings:

    def __init__(self, irrigation, config):
        self.irrigation = irrigation
        self.config = config

    def run_scenario(self, scenario):

        print(f"\n🚀 {scenario.name}")

        config_data = self.config.get_program_configuration(
        scenario.program_id
        )

        print()
        print("========== PROGRAM CONFIG ==========")
        print(config_data)
        print("====================================")

        print("\n========== PROGRAMS INFO ==========")
        print(self.irrigation.programs_info().response)

        print("\n========== SHIFTS INFO ==========")
        print(self.irrigation.shifts_info().response)

        print("\n========== RECIPES INFO ==========")
        print(self.irrigation.recipes_info().response)

        print("\n==================================\n")

        result = self.irrigation.run_program(
            scenario.program_id
        )

        assert result.success, result.response

        print(
            f"Waiting {scenario.wait_time_sec + 2}s..."
        )

        time.sleep(
            scenario.wait_time_sec + 2
        )

        print("\n========== RAW REPORT ==========")

        report = self.irrigation.completed_report(
            scenario.program_id
        )

        print(report.response)

        completed_report = (
            ReportParser.extract_completed_report(
                report.response
            )
        )

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

        assert finish_reason == "Completed", (
            f"Expected finish reason 'Completed' "
            f"but got '{finish_reason}'"
        )

        data = (
            ReportParser.parse_completed_report(
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

        self.validate_results(
            scenario,
            data,
        )

        print(f"✅ {scenario.name} PASSED")
        

    def validate_results(
        self,
        scenario,
        data,
    ):

        print("\n========== EXPECTED ==========")
        print(f"Expected Water     : {scenario.expected_water}")
        print(f"Expected Dosing    : {scenario.expected_dosing}")
        print(f"Expected Remaining : {scenario.expected_remaining}")
        print("==============================\n")

        assert self.verify_tolerance(
            actual=data["water_delivered"],
            expected=scenario.expected_water,
            tolerance_percent=scenario.water_tolerance_percent,
        ), (
            f"Water mismatch. "
            f"Expected={scenario.expected_water}, "
            f"Actual={data['water_delivered']}"
        )

        if scenario.expected_plan_amount:

            actual_plan_amount = (
                data["dosing_delivered"]
                + data["dosing_remaining"]
            )

            assert self.verify_tolerance(
                actual=actual_plan_amount,
                expected=scenario.expected_plan_amount,
                tolerance_percent=1,
            ), (
                f"Plan amount mismatch. "
                f"Expected={scenario.expected_plan_amount}, "
                f"Actual={actual_plan_amount}"
            )

        else:

            assert self.verify_tolerance(
                actual=data["dosing_delivered"],
                expected=scenario.expected_dosing,
                tolerance_percent=scenario.dosing_tolerance_percent,
            ), (
                f"Dosing mismatch. "
                f"Expected={scenario.expected_dosing}, "
                f"Actual={data['dosing_delivered']}"
            )

            assert self.verify_tolerance(
                actual=data["dosing_remaining"],
                expected=scenario.expected_remaining,
                tolerance_percent=scenario.remaining_tolerance_percent,
            ), (
                f"Remaining mismatch. "
                f"Expected={scenario.expected_remaining}, "
                f"Actual={data['dosing_remaining']}"
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
        scenario,
    ):

        timeout = time.time() + 60

        while time.time() < timeout:

            report = self.irrigation.completed_report(
                scenario.program_id
            )

            completed_report = (
                ReportParser.extract_completed_report(
                    report.response
                )
            )

            data = (
                ReportParser.parse_completed_report(
                    completed_report
                )
            )

            total = (
                data["dosing_delivered"]
                + data["dosing_remaining"]
            )

            if (
                scenario.expected_plan_amount
                and total == scenario.expected_plan_amount
            ):
                return completed_report

            time.sleep(5)

        raise TimeoutError(
            "Completed report did not stabilize"
        )