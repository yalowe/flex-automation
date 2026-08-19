import argparse
import os
from pathlib import Path

from flex.controller import FlexController
from flex.irrigation import IrrigationService
from services.flex_gui_service import FlexGuiSession
from services.monitoring_service import MonitoringService
from services.flex_config_service import FlexConfigService

from runner.programs_and_dosings import ProgramsAndDosings

from scenarios import (
    # BULK_TIME_TIME_PROGRAM,
    # BULK_TIME_QUANTITY_PROGRAM,
    # BULK_TIME_DEPTH_PROGRAM,
    # BULK_QUANTITY_TIME_PROGRAM,
    # BULK_QUANTITY_QUANTITY_PROGRAM,
    # SPREAD_TIME_TIME_PROGRAM,
    SPREAD_QUANTITY_QUANTITY_PROGRAM,
    # CALCULATED_QUANTITY_PROGRAM,
)

ROOT = Path(__file__).resolve().parent
WM_SETTINGS_PATH = ROOT / "Flex_tester" / "wm_settings.json"
FLEX_GUI_LAUNCHER = ROOT / "Flex_tester" / "launch_flex_gui.py"
FLEX_GUI_PORT = "COM10"
FLEX_GUI_BAUD = 115200

SCENARIOS = [
    # BULK_TIME_TIME_PROGRAM,
    # BULK_TIME_QUANTITY_PROGRAM,
    # BULK_TIME_DEPTH_PROGRAM,
    # BULK_QUANTITY_TIME_PROGRAM,
    # BULK_QUANTITY_QUANTITY_PROGRAM,
    # SPREAD_TIME_TIME_PROGRAM,
    SPREAD_QUANTITY_QUANTITY_PROGRAM,
    # CALCULATED_QUANTITY_PROGRAM,
]

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FLEX automation runner")
    parser.add_argument(
        "--port",
        default=os.getenv("FLEX_PORT", "COM5"),
        help="Serial port (default: FLEX_PORT env or COM5)",
    )
    parser.add_argument(
        "--baud",
        type=int,
        default=int(os.getenv("FLEX_BAUD", "115200")),
        help="Serial baud rate (default: FLEX_BAUD env or 115200)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=int(os.getenv("FLEX_RUNS", "1")),
        help="Number of full scenario loops (default: FLEX_RUNS env or 1)",
    )
    parser.add_argument(
        "--dry-run-config",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Print effective configuration and exit without connecting to hardware",
    )
    return parser.parse_args()


def print_effective_config(args: argparse.Namespace) -> None:
    print("========== EFFECTIVE CONFIG ==========")
    print(f"Port                  : {args.port}")
    print(f"Baud                  : {args.baud}")
    print(f"Runs                  : {max(0, args.runs)}")
    print(f"Flex GUI Port         : {FLEX_GUI_PORT}")
    print(f"Flex GUI Baud         : {FLEX_GUI_BAUD}")
    print(f"WM Settings           : {WM_SETTINGS_PATH}")
    print(
        "Active Scenarios       : "
        + ", ".join(f"{scenario.name}#{scenario.program_id}" for scenario in SCENARIOS)
    )
    print("======================================")

def main(args: argparse.Namespace):
    if args.dry_run_config:
        print_effective_config(args)
        return

    controller = FlexController(args.port, baudrate=args.baud)

    monitoring = MonitoringService("logs")
    session_dir = monitoring.start_session()

    print(f"Monitoring session: {session_dir}")

    controller.set_monitoring_service(monitoring)
    controller.connect()

    irrigation = IrrigationService(controller)
    config = FlexConfigService(
        controller,
        wm_settings_path=WM_SETTINGS_PATH,
    )
    flex_gui_session = FlexGuiSession(
        launcher_script=FLEX_GUI_LAUNCHER,
        port=FLEX_GUI_PORT,
        baud=FLEX_GUI_BAUD,
        wm_settings_path=WM_SETTINGS_PATH,
    )
    print(
        "Launching Flex GUI early: "
        f"port={FLEX_GUI_PORT}, baud={FLEX_GUI_BAUD}"
    )
    flex_gui_session.launch()

    e2e_tests = ProgramsAndDosings(
        irrigation=irrigation,
        config=config,
        flex_gui_session=flex_gui_session,
    )

    print(
        "Run settings: "
        f"port={args.port}, baud={args.baud}, runs={max(0, args.runs)}, "
        "fail_on_anomalies=True"
    )

    try:
        e2e_tests.run_all(SCENARIOS, run_count=args.runs)

    finally:
        e2e_tests.close()
        controller.disconnect()


if __name__ == "__main__":
    main(parse_args())
