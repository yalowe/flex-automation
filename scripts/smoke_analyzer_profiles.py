from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from main import apply_analyzer_profile


def _args(**overrides) -> argparse.Namespace:
    base = {
        "analyzer_profile": "off",
        "analyzer_policy": "off",
        "analyzer_policy_map": "",
        "analyzer_default_policy": "safe",
    }
    base.update(overrides)
    return argparse.Namespace(**base)


def main() -> None:
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

    print("smoke_analyzer_profiles: PASS")


if __name__ == "__main__":
    main()
