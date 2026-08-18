"""Consolidated smoke tests for analyzer profile/policy CLI behavior in main.py.

Merged from (each check preserves the original assertions verbatim):
smoke_analyzer_profiles, smoke_analyzer_profiles_file_fallback,
smoke_auto_analyzer_profile, smoke_invalid_analyzer_profiles_file,
smoke_list_explain_profiles, smoke_dry_run_config, smoke_explain_auto_profile,
smoke_list_scenarios, smoke_main_analyzer_policy_wiring,
smoke_policy_map_resolution, smoke_invalid_policy_map.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import main as runner_main
from main import apply_analyzer_profile, configure_analyzer_policy_hook
from runner.programs_and_dosings import _resolve_analyzer_policy_for_program

PYTHON = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
MAIN = REPO_ROOT / "main.py"


def _args(**overrides) -> argparse.Namespace:
    base = {
        "analyzer_profile": "off",
        "analyzer_policy": "off",
        "analyzer_policy_map": "",
        "analyzer_default_policy": "safe",
    }
    base.update(overrides)
    return argparse.Namespace(**base)


def _profile_args(profile_name: str) -> argparse.Namespace:
    return argparse.Namespace(
        analyzer_profile=profile_name,
        analyzer_policy="off",
        analyzer_policy_map="",
        analyzer_default_policy="safe",
        analyzer_profiles=runner_main.load_analyzer_profiles(),
    )


def _run_main(*args: str) -> str:
    cmd = [str(PYTHON), str(MAIN), *args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    text = (result.stdout or "") + (result.stderr or "")
    assert result.returncode == 0, text
    return text


def check_analyzer_profiles() -> None:
    args = apply_analyzer_profile(_args(analyzer_profile="spread7-strict"))
    assert args.analyzer_policy == "safe"
    assert args.analyzer_policy_map == "7:strict,*:safe"
    assert args.analyzer_default_policy == "safe"

    args = apply_analyzer_profile(_args(analyzer_profile="spread7-strict-calc8-lab"))
    assert args.analyzer_policy == "safe"
    assert args.analyzer_policy_map == "7:strict,8:lab,*:safe"

    args = apply_analyzer_profile(
        _args(
            analyzer_profile="spread7-strict",
            analyzer_policy="strict",
            analyzer_policy_map="7:lab,*:strict",
            analyzer_default_policy="lab",
        )
    )
    assert args.analyzer_policy == "strict"
    assert args.analyzer_policy_map == "7:lab,*:strict"
    assert args.analyzer_default_policy == "lab"
    print("check_analyzer_profiles: PASS")


def check_analyzer_profiles_file_fallback() -> None:
    missing_file = REPO_ROOT / "config" / "__missing_analyzer_profiles__.json"
    profiles = runner_main.load_analyzer_profiles(str(missing_file))
    assert "off" in profiles
    assert "spread7-strict" in profiles
    assert profiles["spread7-strict"]["policy_map"] == "7:strict,*:safe"
    print("check_analyzer_profiles_file_fallback: PASS")


def check_auto_analyzer_profile() -> None:
    original_scenarios = runner_main.SCENARIOS
    try:
        runner_main.SCENARIOS = [type("Scenario", (), {"program_id": 7})()]
        args = runner_main.apply_analyzer_profile(_profile_args("auto"))
        assert args.analyzer_profile == "spread7-strict"
        assert args.analyzer_policy == "safe"
        assert args.analyzer_policy_map == "7:strict,*:safe"

        runner_main.SCENARIOS = [
            type("Scenario", (), {"program_id": 7})(),
            type("Scenario", (), {"program_id": 8})(),
        ]
        args = runner_main.apply_analyzer_profile(_profile_args("auto"))
        assert args.analyzer_profile == "spread7-strict-calc8-lab"
        assert args.analyzer_policy_map == "7:strict,8:lab,*:safe"

        runner_main.SCENARIOS = [type("Scenario", (), {"program_id": 3})()]
        args = runner_main.apply_analyzer_profile(_profile_args("auto"))
        assert args.analyzer_profile == "off"
        assert args.analyzer_policy == "off"
        print("check_auto_analyzer_profile: PASS")
    finally:
        runner_main.SCENARIOS = original_scenarios


def check_invalid_analyzer_profiles_file() -> None:
    tmp_dir = REPO_ROOT / "config" / "_smoke_invalid_profiles"
    tmp_file = tmp_dir / "analyzer_profiles_invalid.json"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    bad_profiles = {
        "bad-profile": {
            "policy": "safe",
            "policy_map": "7-strict,*:safe",
            "default_policy": "safe",
        }
    }
    tmp_file.write_text(json.dumps(bad_profiles, indent=2), encoding="utf-8")

    try:
        runner_main.load_analyzer_profiles(str(tmp_file))
    except RuntimeError as exc:
        text = str(exc)
        assert "Invalid analyzer profile 'bad-profile'" in text, text
        assert "Expected format <program_id>:<policy> or *:<policy>" in text, text
        print("check_invalid_analyzer_profiles_file: PASS")
        return

    raise AssertionError("Expected invalid analyzer profiles file to fail")


def check_list_explain_profiles() -> None:
    listed = _run_main("--list-analyzer-profiles")
    assert "ANALYZER PROFILES" in listed, listed
    assert "spread7-strict" in listed, listed
    assert "spread7-strict-calc8-lab" in listed, listed

    explained = _run_main("--explain-analyzer-profile", "spread7-strict")
    assert "Requested Name   : spread7-strict" in explained, explained
    assert "Policy Map       : 7:strict,*:safe" in explained, explained

    explained_auto = _run_main("--explain-analyzer-profile", "auto")
    assert "Requested Name   : auto" in explained_auto, explained_auto
    assert "Resolved Name    : spread7-strict" in explained_auto, explained_auto
    print("check_list_explain_profiles: PASS")


def check_dry_run_config() -> None:
    text = _run_main("--analyzer-profile", "auto", "--dry-run-config")
    assert "========== EFFECTIVE CONFIG ==========" in text, text
    assert "Analyzer Profile      : spread7-strict-calc8-lab" in text, text
    assert "Analyzer Policy Map   : 7:strict,8:lab,*:safe" in text, text
    assert "Active Scenarios       : Bulk By Time - Time#1" in text, text
    print("check_dry_run_config: PASS")


def check_explain_auto_profile() -> None:
    stdout = _run_main("--explain-auto-profile")
    assert "ANALYZER PROFILE" in stdout, stdout
    assert "Requested Name   : auto" in stdout, stdout
    assert "Resolved Name    : spread7-strict" in stdout, stdout
    assert "Policy           : safe" in stdout, stdout
    print("check_explain_auto_profile: PASS")


def check_list_scenarios() -> None:
    stdout = _run_main("--list-scenarios")
    assert "ACTIVE SCENARIOS" in stdout, stdout
    assert "Program ID" in stdout, stdout
    assert "Spread By Quantity" in stdout, stdout
    print("check_list_scenarios: PASS")


def check_main_analyzer_policy_wiring() -> None:
    def make_args(policy: str) -> argparse.Namespace:
        script = REPO_ROOT / "scripts" / "headless_monitor_policy.py"
        return argparse.Namespace(
            analyzer_policy=policy,
            analyzer_policy_script=str(script),
            analyzer_policy_map="",
            analyzer_default_policy="safe",
        )

    original_cmd = os.environ.get("FLEX_HEADLESS_ANALYZER_CMD")
    original_strict = os.environ.get("FLEX_HEADLESS_ANALYZER_STRICT")
    try:
        os.environ.pop("FLEX_HEADLESS_ANALYZER_CMD", None)
        os.environ.pop("FLEX_HEADLESS_ANALYZER_STRICT", None)

        configure_analyzer_policy_hook(make_args("safe"))
        assert "--policy safe" in os.environ.get("FLEX_HEADLESS_ANALYZER_CMD", "")
        assert os.environ.get("FLEX_HEADLESS_ANALYZER_STRICT") == "false"

        os.environ.pop("FLEX_HEADLESS_ANALYZER_CMD", None)
        os.environ.pop("FLEX_HEADLESS_ANALYZER_STRICT", None)

        configure_analyzer_policy_hook(make_args("strict"))
        assert "--policy strict" in os.environ.get("FLEX_HEADLESS_ANALYZER_CMD", "")
        assert os.environ.get("FLEX_HEADLESS_ANALYZER_STRICT") == "true"

        os.environ.pop("FLEX_HEADLESS_ANALYZER_CMD", None)
        os.environ.pop("FLEX_HEADLESS_ANALYZER_STRICT", None)

        configure_analyzer_policy_hook(make_args("off"))
        assert os.environ.get("FLEX_HEADLESS_ANALYZER_CMD") is None
        print("check_main_analyzer_policy_wiring: PASS")
    finally:
        if original_cmd is None:
            os.environ.pop("FLEX_HEADLESS_ANALYZER_CMD", None)
        else:
            os.environ["FLEX_HEADLESS_ANALYZER_CMD"] = original_cmd
        if original_strict is None:
            os.environ.pop("FLEX_HEADLESS_ANALYZER_STRICT", None)
        else:
            os.environ["FLEX_HEADLESS_ANALYZER_STRICT"] = original_strict


def check_policy_map_resolution() -> None:
    orig_map = os.environ.get("FLEX_HEADLESS_ANALYZER_POLICY_MAP")
    orig_default = os.environ.get("FLEX_HEADLESS_ANALYZER_DEFAULT_POLICY")
    try:
        os.environ["FLEX_HEADLESS_ANALYZER_POLICY_MAP"] = "7:strict,8:lab,*:safe"
        os.environ["FLEX_HEADLESS_ANALYZER_DEFAULT_POLICY"] = "safe"

        assert _resolve_analyzer_policy_for_program(7) == "strict"
        assert _resolve_analyzer_policy_for_program(8) == "lab"
        assert _resolve_analyzer_policy_for_program(3) == "safe"

        os.environ["FLEX_HEADLESS_ANALYZER_POLICY_MAP"] = ""
        os.environ["FLEX_HEADLESS_ANALYZER_DEFAULT_POLICY"] = "lab"
        assert _resolve_analyzer_policy_for_program(7) == "lab"
        print("check_policy_map_resolution: PASS")
    finally:
        if orig_map is None:
            os.environ.pop("FLEX_HEADLESS_ANALYZER_POLICY_MAP", None)
        else:
            os.environ["FLEX_HEADLESS_ANALYZER_POLICY_MAP"] = orig_map
        if orig_default is None:
            os.environ.pop("FLEX_HEADLESS_ANALYZER_DEFAULT_POLICY", None)
        else:
            os.environ["FLEX_HEADLESS_ANALYZER_DEFAULT_POLICY"] = orig_default


def check_invalid_policy_map() -> None:
    cmd = [
        str(PYTHON),
        str(MAIN),
        "--analyzer-policy",
        "safe",
        "--analyzer-policy-map",
        "7-strict,*:safe",
        "--runs",
        "0",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    combined = (result.stdout or "") + "\n" + (result.stderr or "")
    assert result.returncode != 0, "Expected non-zero exit for invalid policy map"
    assert "Invalid analyzer policy configuration" in combined, combined
    assert "Expected format <program_id>:<policy> or *:<policy>" in combined, combined
    print("check_invalid_policy_map: PASS")


CHECKS = [
    check_analyzer_profiles,
    check_analyzer_profiles_file_fallback,
    check_auto_analyzer_profile,
    check_invalid_analyzer_profiles_file,
    check_list_explain_profiles,
    check_dry_run_config,
    check_explain_auto_profile,
    check_list_scenarios,
    check_main_analyzer_policy_wiring,
    check_policy_map_resolution,
    check_invalid_policy_map,
]


def main() -> None:
    for check in CHECKS:
        check()
    print("smoke_analyzer_cli: ALL PASS")


if __name__ == "__main__":
    main()
