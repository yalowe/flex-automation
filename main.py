import argparse
import os
from pathlib import Path

from flex.controller import FlexController
from services.analyzer_policy import VALID_ANALYZER_POLICIES
from services.analyzer_profile_service import (
    configure_analyzer_policy_hook,
    explain_analyzer_profile as _explain_analyzer_profile,
    list_analyzer_profiles,
    load_analyzer_profiles,
    default_analyzer_profiles_path as _default_analyzer_profiles_path,
    apply_analyzer_profile as _apply_analyzer_profile,
    validate_analyzer_policy_settings,
)
from services.flex_gui_service import FlexGuiSession, run_wm_sync_if_enabled
from services.irrigation_service import IrrigationService
from services.monitoring_service import MonitoringService
from services.flex_config_service import FlexConfigService

from runner.programs_and_dosings import ProgramsAndDosings

from scenarios import (
    BULK_TIME_TIME_PROGRAM,
    BULK_TIME_QUANTITY_PROGRAM,
    BULK_TIME_DEPTH_PROGRAM,
    BULK_QUANTITY_TIME_PROGRAM,
    BULK_QUANTITY_QUANTITY_PROGRAM,
    SPREAD_TIME_TIME_PROGRAM,
    SPREAD_QUANTITY_QUANTITY_PROGRAM,
    CALCULATED_QUANTITY_PROGRAM,
)

SCENARIOS = [
    BULK_TIME_TIME_PROGRAM,
    BULK_TIME_QUANTITY_PROGRAM,
    BULK_TIME_DEPTH_PROGRAM,
    BULK_QUANTITY_TIME_PROGRAM,
    BULK_QUANTITY_QUANTITY_PROGRAM,
    SPREAD_TIME_TIME_PROGRAM,
    SPREAD_QUANTITY_QUANTITY_PROGRAM,
    CALCULATED_QUANTITY_PROGRAM,
]


def apply_analyzer_profile(args: argparse.Namespace) -> argparse.Namespace:
    return _apply_analyzer_profile(args, SCENARIOS)


def explain_analyzer_profile(args: argparse.Namespace, profile_name: str) -> None:
    _explain_analyzer_profile(args, profile_name, SCENARIOS)


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    value = raw_value.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False

    return default


def parse_args() -> argparse.Namespace:
    analyzer_profiles = load_analyzer_profiles(
        os.getenv("FLEX_ANALYZER_PROFILES_FILE", _default_analyzer_profiles_path())
    )
    default_sync_script = str(
        Path(__file__).resolve().parent / "Flex_tester" / "sync_wm_settings_to_board.py"
    )
    default_sync_settings = str(
        Path(__file__).resolve().parent / "Flex_tester" / "wm_settings.json"
    )
    default_flex_gui_launcher = str(
        Path(__file__).resolve().parent / "Flex_tester" / "launch_flex_gui.py"
    )
    default_analyzer_policy_script = str(
        Path(__file__).resolve().parent / "scripts" / "headless_monitor_policy.py"
    )

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
        "--fail-on-anomalies",
        action=argparse.BooleanOptionalAction,
        default=_env_bool("FLEX_FAIL_ON_ANOMALIES", True),
        help="Fail scenario when blocked anomalies are detected",
    )
    parser.add_argument(
        "--wm-sync",
        action=argparse.BooleanOptionalAction,
        default=_env_bool("FLEX_WM_SYNC", False),
        help="Run Flex_tester WM sync tool before controller connection",
    )
    parser.add_argument(
        "--wm-sync-strict",
        action=argparse.BooleanOptionalAction,
        default=_env_bool("FLEX_WM_SYNC_STRICT", False),
        help="Fail startup if WM sync fails (default: warning only)",
    )
    parser.add_argument(
        "--wm-sync-script",
        default=os.getenv("FLEX_WM_SYNC_SCRIPT", default_sync_script),
        help="Path to Flex_tester/sync_wm_settings_to_board.py",
    )
    parser.add_argument(
        "--wm-sync-settings",
        default=os.getenv("FLEX_WM_SYNC_SETTINGS", default_sync_settings),
        help="Path to wm_settings.json used by WM sync tool",
    )
    parser.add_argument(
        "--flex-gui",
        action=argparse.BooleanOptionalAction,
        default=_env_bool("FLEX_GUI", True),
        help="Open Flex GUI before each scenario, auto-connect to COM10 WM simulator, and preload WM fields (use --no-flex-gui to disable)",
    )
    parser.add_argument(
        "--flex-gui-port",
        default=os.getenv("FLEX_GUI_PORT", "COM10"),
        help="Serial port used by Flex GUI WM simulator connection",
    )
    parser.add_argument(
        "--flex-gui-baud",
        type=int,
        default=int(os.getenv("FLEX_GUI_BAUD", "115200")),
        help="Baud rate used by Flex GUI WM simulator connection",
    )
    parser.add_argument(
        "--flex-gui-launcher",
        default=os.getenv("FLEX_GUI_LAUNCHER", default_flex_gui_launcher),
        help="Path to Flex GUI launcher script",
    )
    parser.add_argument(
        "--analyzer-policy",
        choices=sorted(VALID_ANALYZER_POLICIES),
        default=os.getenv("FLEX_ANALYZER_POLICY", "off"),
        help="Auto-wire headless analyzer hook policy (default: off)",
    )
    parser.add_argument(
        "--analyzer-profile",
        choices=sorted(set(analyzer_profiles) | {"auto"}),
        default=os.getenv("FLEX_ANALYZER_PROFILE", "off"),
        help="Named analyzer preset that can populate policy and policy map",
    )
    parser.add_argument(
        "--analyzer-profiles-file",
        default=os.getenv(
            "FLEX_ANALYZER_PROFILES_FILE", _default_analyzer_profiles_path()
        ),
        help="Path to analyzer profiles JSON file",
    )
    parser.add_argument(
        "--analyzer-policy-script",
        default=os.getenv(
            "FLEX_ANALYZER_POLICY_SCRIPT",
            default_analyzer_policy_script,
        ),
        help="Path to scripts/headless_monitor_policy.py",
    )
    parser.add_argument(
        "--analyzer-policy-map",
        default=os.getenv("FLEX_ANALYZER_POLICY_MAP", ""),
        help='Per-program policy mapping, e.g. "7:strict,*:safe"',
    )
    parser.add_argument(
        "--analyzer-default-policy",
        default=os.getenv("FLEX_ANALYZER_DEFAULT_POLICY", "safe"),
        help="Fallback policy when mapping has no exact program match",
    )
    parser.add_argument(
        "--dry-run-config",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Print effective configuration and exit without connecting to hardware",
    )
    parser.add_argument(
        "--list-analyzer-profiles",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="List loaded analyzer profiles and exit",
    )
    parser.add_argument(
        "--explain-analyzer-profile",
        default="",
        help="Show details for one analyzer profile name and exit",
    )
    parser.add_argument(
        "--list-scenarios",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="List active scenarios and exit",
    )
    parser.add_argument(
        "--explain-auto-profile",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Explain the auto-resolved analyzer profile and exit",
    )
    args = parser.parse_args()
    args.analyzer_profiles = analyzer_profiles
    return args


def print_effective_config(args: argparse.Namespace) -> None:
    print("========== EFFECTIVE CONFIG ==========")
    print(f"Port                  : {args.port}")
    print(f"Baud                  : {args.baud}")
    print(f"Runs                  : {max(0, args.runs)}")
    print(f"Fail On Anomalies     : {args.fail_on_anomalies}")
    print(f"WM Sync               : {args.wm_sync}")
    print(f"WM Sync Strict        : {args.wm_sync_strict}")
    print(f"WM Sync Script        : {args.wm_sync_script}")
    print(f"WM Sync Settings      : {args.wm_sync_settings}")
    print(f"Flex GUI              : {args.flex_gui}")
    print(f"Flex GUI Port         : {args.flex_gui_port}")
    print(f"Flex GUI Baud         : {args.flex_gui_baud}")
    print(f"Flex GUI Launcher     : {args.flex_gui_launcher}")
    print(f"Analyzer Profile      : {args.analyzer_profile}")
    print(f"Analyzer Policy       : {args.analyzer_policy}")
    print(f"Analyzer Policy Map   : {args.analyzer_policy_map or 'none'}")
    print(f"Analyzer Default      : {args.analyzer_default_policy}")
    print(f"Profiles File         : {args.analyzer_profiles_file}")
    print(f"Policy Script         : {args.analyzer_policy_script}")
    print(
        "Active Scenarios       : "
        + ", ".join(f"{scenario.name}#{scenario.program_id}" for scenario in SCENARIOS)
    )
    print("======================================")


def list_scenarios() -> None:
    print("========== ACTIVE SCENARIOS ==========")
    for scenario in SCENARIOS:
        print(f"  {scenario.name:<35} (Program ID {scenario.program_id})")
    print("======================================")


def explain_auto_profile(args: argparse.Namespace) -> None:
    explain_analyzer_profile(args, "auto")


def main(args: argparse.Namespace):
    if args.list_scenarios:
        list_scenarios()
        return

    if args.explain_auto_profile:
        explain_auto_profile(args)
        return

    args = apply_analyzer_profile(args)

    if args.list_analyzer_profiles:
        list_analyzer_profiles(args)
        return

    if args.explain_analyzer_profile:
        explain_analyzer_profile(args, args.explain_analyzer_profile)
        return

    if args.dry_run_config:
        validate_analyzer_policy_settings(args)
        print_effective_config(args)
        return

    configure_analyzer_policy_hook(args)

    run_wm_sync_if_enabled(args)

    controller = FlexController(args.port, baudrate=args.baud)

    monitoring = MonitoringService("logs")
    session_dir = monitoring.start_session()

    print(f"Monitoring session: {session_dir}")

    controller.set_monitoring_service(monitoring)
    controller.connect()

    irrigation = IrrigationService(controller)
    config = FlexConfigService(
        controller,
        wm_settings_path=args.wm_sync_settings,
    )
    flex_gui_session = None

    if args.flex_gui:
        flex_gui_session = FlexGuiSession(
            launcher_script=args.flex_gui_launcher,
            port=args.flex_gui_port,
            baud=args.flex_gui_baud,
            wm_settings_path=args.wm_sync_settings,
        )
        print(
            "Launching Flex GUI early: "
            f"port={args.flex_gui_port}, baud={args.flex_gui_baud}"
        )
        flex_gui_session.launch()

    e2e_tests = ProgramsAndDosings(
        irrigation=irrigation,
        config=config,
        fail_on_anomalies=args.fail_on_anomalies,
        flex_gui_session=flex_gui_session,
    )

    print(
        "Run settings: "
        f"port={args.port}, baud={args.baud}, runs={max(0, args.runs)}, "
        f"fail_on_anomalies={args.fail_on_anomalies}, "
        f"wm_sync={args.wm_sync}, wm_sync_strict={args.wm_sync_strict}, "
        f"analyzer_profile={args.analyzer_profile}, "
        f"analyzer_policy={args.analyzer_policy}, "
        f"analyzer_policy_map={args.analyzer_policy_map or 'none'}, "
        f"analyzer_default_policy={args.analyzer_default_policy}"
    )

    try:
        e2e_tests.run_all(SCENARIOS, run_count=args.runs)

    finally:
        e2e_tests.close()
        controller.disconnect()


if __name__ == "__main__":
    main(parse_args())
