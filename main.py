import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from flex.controller import FlexController
from services.analyzer_policy import (
    AnalyzerPolicyConfigError,
    VALID_ANALYZER_POLICIES,
    normalize_runtime_policy,
    parse_policy_map,
)
from services.flex_gui_service import FlexGuiSession
from services.irrigation_service import IrrigationService
from services.monitoring_service import MonitoringService
from services.flex_config_service import FlexConfigService

from tests.programs_and_dosings import ProgramsAndDosings

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

DEFAULT_ANALYZER_PROFILES = {
    "off": {
        "policy": "off",
        "policy_map": "",
        "default_policy": "safe",
    },
    "spread7-strict": {
        "policy": "safe",
        "policy_map": "7:strict,*:safe",
        "default_policy": "safe",
    },
    "spread7-strict-calc8-lab": {
        "policy": "safe",
        "policy_map": "7:strict,8:lab,*:safe",
        "default_policy": "safe",
    },
}


def _default_analyzer_profiles_path() -> str:
    return str(Path(__file__).resolve().parent / "config" / "analyzer_profiles.json")


def load_analyzer_profiles(config_path: str | None = None) -> dict[str, dict[str, str]]:
    path = Path(config_path or _default_analyzer_profiles_path())

    if not path.exists():
        return dict(DEFAULT_ANALYZER_PROFILES)

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(
            f"Failed to load analyzer profiles from {path}: {exc}"
        ) from exc

    if not isinstance(raw, dict):
        raise RuntimeError(
            f"Invalid analyzer profiles file {path}: root JSON value must be an object"
        )

    profiles: dict[str, dict[str, str]] = {}
    for name, entry in raw.items():
        if not isinstance(name, str) or not isinstance(entry, dict):
            raise RuntimeError(
                f"Invalid analyzer profile entry in {path}: expected object members"
            )

        policy = str(entry.get("policy", "off")).strip().lower()
        policy_map = str(entry.get("policy_map", ""))
        default_policy = str(entry.get("default_policy", "safe")).strip().lower()

        if policy not in VALID_ANALYZER_POLICIES:
            allowed = ", ".join(sorted(VALID_ANALYZER_POLICIES))
            raise RuntimeError(
                f"Invalid analyzer profile '{name}' in {path}: policy '{policy}' is not one of {allowed}"
            )

        if policy == "off":
            if policy_map.strip():
                raise RuntimeError(
                    f"Invalid analyzer profile '{name}' in {path}: policy_map is not allowed when policy is 'off'"
                )
        else:
            try:
                normalize_runtime_policy(
                    default_policy, f"default policy for profile '{name}'"
                )
                parse_policy_map(policy_map, default_policy)
            except AnalyzerPolicyConfigError as exc:
                raise RuntimeError(
                    f"Invalid analyzer profile '{name}' in {path}: {exc}"
                ) from exc

        profiles[name] = {
            "policy": policy,
            "policy_map": policy_map,
            "default_policy": default_policy,
        }

    return profiles


def _detect_auto_analyzer_profile() -> str:
    active_program_ids = {scenario.program_id for scenario in SCENARIOS}

    if 7 in active_program_ids and 8 in active_program_ids:
        return "spread7-strict-calc8-lab"

    if 7 in active_program_ids:
        return "spread7-strict"

    return "off"


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


def apply_analyzer_profile(args: argparse.Namespace) -> argparse.Namespace:
    if args.analyzer_profile == "auto":
        args.analyzer_profile = _detect_auto_analyzer_profile()

    profile = getattr(args, "analyzer_profiles", DEFAULT_ANALYZER_PROFILES).get(
        args.analyzer_profile
    )
    if not profile or args.analyzer_profile == "off":
        return args

    if args.analyzer_policy == "off":
        args.analyzer_policy = profile["policy"]

    if not args.analyzer_policy_map.strip():
        args.analyzer_policy_map = profile["policy_map"]

    default_policy = (args.analyzer_default_policy or "").strip().lower()
    if default_policy == "safe" and profile["default_policy"] != "safe":
        args.analyzer_default_policy = profile["default_policy"]

    if profile["default_policy"] == "safe" and not args.analyzer_default_policy.strip():
        args.analyzer_default_policy = "safe"

    return args


def validate_analyzer_policy_settings(args: argparse.Namespace) -> None:
    if args.analyzer_policy == "off":
        return

    try:
        parse_policy_map(
            mapping_text=args.analyzer_policy_map,
            default_policy=args.analyzer_default_policy,
        )
    except AnalyzerPolicyConfigError as exc:
        raise RuntimeError(f"Invalid analyzer policy configuration: {exc}") from exc


def configure_analyzer_policy_hook(args: argparse.Namespace) -> None:
    if args.analyzer_policy == "off":
        return

    validate_analyzer_policy_settings(args)

    policy_script = Path(args.analyzer_policy_script)
    if not policy_script.exists():
        raise RuntimeError(f"Analyzer policy script not found: {policy_script}")

    cmd_template = (
        f'{sys.executable} "{policy_script}" '
        f"--policy {args.analyzer_policy} "
        '--session-dir "{session_dir}" '
        '--scenario-name "{scenario_name}" '
        "--program-id {program_id} "
        "--anomaly-count {anomaly_count}"
    )

    if args.analyzer_policy_map.strip():
        cmd_template = (
            f'{sys.executable} "{policy_script}" '
            "--policy {policy} "
            '--session-dir "{session_dir}" '
            '--scenario-name "{scenario_name}" '
            "--program-id {program_id} "
            "--anomaly-count {anomaly_count}"
        )
        os.environ["FLEX_HEADLESS_ANALYZER_POLICY_MAP"] = (
            args.analyzer_policy_map.strip()
        )
        os.environ["FLEX_HEADLESS_ANALYZER_DEFAULT_POLICY"] = (
            args.analyzer_default_policy.strip() or "safe"
        )

    os.environ["FLEX_HEADLESS_ANALYZER_CMD"] = cmd_template

    if "FLEX_HEADLESS_ANALYZER_STRICT" not in os.environ:
        os.environ["FLEX_HEADLESS_ANALYZER_STRICT"] = (
            "true" if args.analyzer_policy == "strict" else "false"
        )

    print("Configured analyzer hook from policy: " f"policy={args.analyzer_policy}")


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


def list_analyzer_profiles(args: argparse.Namespace) -> None:
    print("========== ANALYZER PROFILES ==========")
    for name in sorted(args.analyzer_profiles):
        profile = args.analyzer_profiles[name]
        print(f"{name}")
        print(f"  policy         : {profile['policy']}")
        print(f"  policy_map     : {profile['policy_map'] or 'none'}")
        print(f"  default_policy : {profile['default_policy']}")
    print("=======================================")


def explain_analyzer_profile(args: argparse.Namespace, profile_name: str) -> None:
    name = (profile_name or "").strip()
    if not name:
        raise RuntimeError("--explain-analyzer-profile requires a profile name")

    resolved_name = _detect_auto_analyzer_profile() if name == "auto" else name
    profile = args.analyzer_profiles.get(resolved_name)
    if profile is None:
        available = ", ".join(sorted(set(args.analyzer_profiles) | {"auto"}))
        raise RuntimeError(
            f"Unknown analyzer profile '{name}'. Available profiles: {available}"
        )

    print("========== ANALYZER PROFILE ==========")
    print(f"Requested Name   : {name}")
    print(f"Resolved Name    : {resolved_name}")
    print(f"Policy           : {profile['policy']}")
    print(f"Policy Map       : {profile['policy_map'] or 'none'}")
    print(f"Default Policy   : {profile['default_policy']}")
    print("======================================")


def list_scenarios() -> None:
    print("========== ACTIVE SCENARIOS ==========")
    for scenario in SCENARIOS:
        print(f"  {scenario.name:<35} (Program ID {scenario.program_id})")
    print("======================================")


def explain_auto_profile(args: argparse.Namespace) -> None:
    explain_analyzer_profile(args, "auto")


def run_wm_sync_if_enabled(args: argparse.Namespace) -> None:
    if not args.wm_sync:
        return

    script_path = Path(args.wm_sync_script)
    settings_path = Path(args.wm_sync_settings)

    if not script_path.exists():
        msg = f"WM sync script not found: {script_path}"
        if args.wm_sync_strict:
            raise RuntimeError(msg)
        print(f"Warning: {msg}")
        return

    if not settings_path.exists():
        msg = f"WM sync settings not found: {settings_path}"
        if args.wm_sync_strict:
            raise RuntimeError(msg)
        print(f"Warning: {msg}")
        return

    cmd = [
        sys.executable,
        str(script_path),
        "--port",
        args.port,
        "--baud",
        str(args.baud),
        "--settings",
        str(settings_path),
    ]

    print("Running WM sync before test run...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())

    if result.returncode != 0:
        msg = "WM sync failed " f"(exit_code={result.returncode})."
        if args.wm_sync_strict:
            raise RuntimeError(msg)
        print(f"Warning: {msg}")
        return

    print("WM sync completed successfully.")


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


def run_nightly(e2e_tests, run_count: int = 1):
    run_number = max(0, run_count)

    stats = {
        scenario.name: {
            "pass": 0,
            "fail": 0,
        }
        for scenario in SCENARIOS
    }

    while run_number > 0:
        print("=" * 100)
        # print(f"FULL RUN #{run_number}")

        for scenario in SCENARIOS:
            print("-" * 100)
            print(f"RUNNING: {scenario.name} " f"(Program ID {scenario.program_id})")
            print("-" * 100)

            try:
                e2e_tests.run_scenario(scenario)

                stats[scenario.name]["pass"] += 1

                print(f"PASSED: {scenario.name} " f"(Program ID {scenario.program_id})")

            except Exception as ex:
                stats[scenario.name]["fail"] += 1

                print(f"FAILED: {scenario.name} " f"(Program ID {scenario.program_id})")

                print(ex)

            time.sleep(10)

        print_summary(stats)

        run_number -= 1


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
        run_nightly(e2e_tests, run_count=args.runs)

    finally:
        e2e_tests.close()
        controller.disconnect()


if __name__ == "__main__":
    main(parse_args())
