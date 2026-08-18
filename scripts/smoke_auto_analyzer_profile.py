from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import main as runner_main


def _profile_args(profile_name: str) -> argparse.Namespace:
    return argparse.Namespace(
        analyzer_profile=profile_name,
        analyzer_policy="off",
        analyzer_policy_map="",
        analyzer_default_policy="safe",
        analyzer_profiles=runner_main.load_analyzer_profiles(),
    )


def main() -> None:
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

        print("smoke_auto_analyzer_profile: PASS")

    finally:
        runner_main.SCENARIOS = original_scenarios


if __name__ == "__main__":
    main()
