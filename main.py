import time
from flex.controller import FlexController
from services.irrigation_service import IrrigationService
from services.monitoring_service import MonitoringService

from tests.programs_and_dosings import ProgramsAndDosings

from services.flex_config_service import (FlexConfigService)



from scenarios import (
    BULK_TIME_TIME_PROGRAM,
    BULK_QUANTITY_TIME_PROGRAM,
    PROPORTIONAL_PROGRAM,
    SPREAD_TIME_PROGRAM,
)

def run_nightly(e2e_tests):

    run_number = 1

    stats = {
        "Bulk By Time": {"pass": 0, "fail": 0},
        "Bulk By Quantity": {"pass": 0, "fail": 0},
        "Spread By Time": {"pass": 0, "fail": 0},
        "Proportional": {"pass": 0, "fail": 0},
    }

    while True:

        print("\n")
        print("=" * 100)
        print(f"FULL RUN #{run_number}")
        print("=" * 100)

        # -------------------------------------------------
        # Proportional
        # -------------------------------------------------
        try:

            e2e_tests.run_scenario(
                PROPORTIONAL_PROGRAM
            )

            stats["Proportional"]["pass"] += 1

        except Exception as ex:

            stats["Proportional"]["fail"] += 1

            print(
                f"\n❌ PROPORTIONAL_PROGRAM FAILED"
            )

            print(ex)

        time.sleep(10)

        # -------------------------------------------------
        # Bulk By Time
        # -------------------------------------------------

        try:

            e2e_tests.run_scenario(
                BULK_TIME_TIME_PROGRAM
            )

            stats["Bulk By Time"]["pass"] += 1

        except Exception as ex:

            stats["Bulk By Time"]["fail"] += 1

            print(
                f"\n❌ BULK_TIME_TIME_PROGRAM FAILED"
            )

            print(ex)

        time.sleep(10)

        # -------------------------------------------------
        # Bulk By Quantity
        # -------------------------------------------------

        try:

            e2e_tests.run_scenario(
                BULK_QUANTITY_TIME_PROGRAM
            )

            stats["Bulk By Quantity"]["pass"] += 1

        except Exception as ex:

            stats["Bulk By Quantity"]["fail"] += 1

            print(
                f"\n❌ BULK_QUANTITY_TIME_PROGRAM FAILED"
            )

            print(ex)

        time.sleep(10)

        # -------------------------------------------------
        # Spread By Time
        # -------------------------------------------------

        try:

            e2e_tests.run_scenario(
                SPREAD_TIME_PROGRAM
            )

            stats["Spread By Time"]["pass"] += 1

        except Exception as ex:

            stats["Spread By Time"]["fail"] += 1

            print(
                f"\n❌ SPREAD_TIME_PROGRAM FAILED"
            )

            print(ex)

        time.sleep(10)

        # -------------------------------------------------
        # Summary
        # -------------------------------------------------

        print("\n")
        print("=" * 100)
        print("CURRENT SUMMARY")
        print("=" * 100)

        print(
            f"Bulk By Time       : "
            f"{stats['Bulk By Time']['pass']} PASS | "
            f"{stats['Bulk By Time']['fail']} FAIL"
        )

        print(
            f"Bulk By Quantity   : "
            f"{stats['Bulk By Quantity']['pass']} PASS | "
            f"{stats['Bulk By Quantity']['fail']} FAIL"
        )

        print(
            f"Spread By Time     : "
            f"{stats['Spread By Time']['pass']} PASS | "
            f"{stats['Spread By Time']['fail']} FAIL"
        )

        print("=" * 100)

        run_number += 1




def main():

    controller = FlexController("COM5")
    monitoring = MonitoringService("logs")
    session_dir = monitoring.start_session()
    print(f"Monitoring session: {session_dir}")
    controller.set_monitoring_service(monitoring)
    controller.connect()
    # calculate_data = FlexConfigService(controller)


    irrigation = IrrigationService(controller)
    config = FlexConfigService(controller)

    e2e_tests = ProgramsAndDosings(irrigation=irrigation, config=config)

    try:
        run_nightly(e2e_tests)

    finally:
        controller.disconnect()

    # for program_id in range(1, 9):

    #     print()
    #     print(f"PROGRAM {program_id}")

    #     program_data = calculate_data.get_program_configuration(program_id)

    #     print(program_data)  



if __name__ == "__main__":
    main()