import json
import os
import sys
from pathlib import Path

from services.analyzer_policy import (
    AnalyzerPolicyConfigError,
    VALID_ANALYZER_POLICIES,
    normalize_runtime_policy,
    parse_policy_map,
)

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


def default_analyzer_profiles_path() -> str:
    return str(Path(__file__).resolve().parents[1] / "config" / "analyzer_profiles.json")


def load_analyzer_profiles(config_path: str | None = None) -> dict[str, dict[str, str]]:
    path = Path(config_path or default_analyzer_profiles_path())

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


def detect_auto_analyzer_profile(scenarios) -> str:
    active_program_ids = {scenario.program_id for scenario in scenarios}

    if 7 in active_program_ids and 8 in active_program_ids:
        return "spread7-strict-calc8-lab"

    if 7 in active_program_ids:
        return "spread7-strict"

    return "off"


def apply_analyzer_profile(args, scenarios):
    if args.analyzer_profile == "auto":
        args.analyzer_profile = detect_auto_analyzer_profile(scenarios)

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


def validate_analyzer_policy_settings(args) -> None:
    if args.analyzer_policy == "off":
        return

    try:
        parse_policy_map(
            mapping_text=args.analyzer_policy_map,
            default_policy=args.analyzer_default_policy,
        )
    except AnalyzerPolicyConfigError as exc:
        raise RuntimeError(f"Invalid analyzer policy configuration: {exc}") from exc


def configure_analyzer_policy_hook(args) -> None:
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


def list_analyzer_profiles(args) -> None:
    print("========== ANALYZER PROFILES ==========")
    for name in sorted(args.analyzer_profiles):
        profile = args.analyzer_profiles[name]
        print(f"{name}")
        print(f"  policy         : {profile['policy']}")
        print(f"  policy_map     : {profile['policy_map'] or 'none'}")
        print(f"  default_policy : {profile['default_policy']}")
    print("=======================================")


def explain_analyzer_profile(args, profile_name: str, scenarios) -> None:
    name = (profile_name or "").strip()
    if not name:
        raise RuntimeError("--explain-analyzer-profile requires a profile name")

    resolved_name = detect_auto_analyzer_profile(scenarios) if name == "auto" else name
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
