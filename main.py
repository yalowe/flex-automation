import time

from flex.controller import FlexController
from services.irrigation_service import IrrigationService
from services.monitoring_service import MonitoringService
from services.flex_config_service import FlexConfigService

from tests.programs_and_dosings import ProgramsAndDosings

from scenarios import (
    # BULK_TIME_TIME_PROGRAM,
    BULK_TIME_QUANTITY_PROGRAM,
    # BULK_TIME_DEPTH_PROGRAM,
    # BULK_QUANTITY_TIME_PROGRAM,
    # BULK_QUANTITY_QUANTITY_PROGRAM,
    # SPREAD_TIME_TIME_PROGRAM,
    # SPREAD_QUANTITY_QUANTITY_PROGRAM,
    # CALCULATED_QUANTITY_PROGRAM,
)


SCENARIOS = [
    # BULK_TIME_TIME_PROGRAM,
    BULK_TIME_QUANTITY_PROGRAM,
    # BULK_TIME_DEPTH_PROGRAM,
    # BULK_QUANTITY_TIME_PROGRAM,
    # BULK_QUANTITY_QUANTITY_PROGRAM,
    # SPREAD_TIME_TIME_PROGRAM,
    # SPREAD_QUANTITY_QUANTITY_PROGRAM,
    # CALCULATED_QUANTITY_PROGRAM,
]


def print_summary(stats):
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


def run_nightly(e2e_tests):
    # run_number = 1

    stats = {
        scenario.name: {
            "pass": 0,
            "fail": 0,
        }
        for scenario in SCENARIOS
    }

    while True:
        print("=" * 100)
        # print(f"FULL RUN #{run_number}")

        for scenario in SCENARIOS:
            print("-" * 100)
            print(
                f"RUNNING: {scenario.name} "
                f"(Program ID {scenario.program_id})"
            )
            print("-" * 100)

            try:
                e2e_tests.run_scenario(scenario)

                stats[scenario.name]["pass"] += 1

                print(
                    f"✅ PASSED: {scenario.name} "
                    f"(Program ID {scenario.program_id})"
                )

            except Exception as ex:
                stats[scenario.name]["fail"] += 1

                print(
                    f"❌ FAILED: {scenario.name} "
                    f"(Program ID {scenario.program_id})"
                )

                print(ex)

            time.sleep(10)

        print_summary(stats)

        # run_number += 1


def main():
    controller = FlexController("COM5")

    monitoring = MonitoringService("logs")
    session_dir = monitoring.start_session()

    print(f"Monitoring session: {session_dir}")

    controller.set_monitoring_service(monitoring)
    controller.connect()

    irrigation = IrrigationService(controller)
    config = FlexConfigService(controller)

    e2e_tests = ProgramsAndDosings(
        irrigation=irrigation,
        config=config,
        fail_on_anomalies=True,
    )

    try:
        run_nightly(e2e_tests)

    finally:
        controller.disconnect()


if __name__ == "__main__":
    main()