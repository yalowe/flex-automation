from __future__ import annotations

import argparse
from pathlib import Path
import os
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from main import configure_analyzer_policy_hook


def _make_args(policy: str) -> argparse.Namespace:
    script = REPO_ROOT / "scripts" / "headless_monitor_policy.py"
    return argparse.Namespace(
        analyzer_policy=policy,
        analyzer_policy_script=str(script),
    )


def main() -> None:
    original_cmd = os.environ.get("FLEX_HEADLESS_ANALYZER_CMD")
    original_strict = os.environ.get("FLEX_HEADLESS_ANALYZER_STRICT")

    try:
        os.environ.pop("FLEX_HEADLESS_ANALYZER_CMD", None)
        os.environ.pop("FLEX_HEADLESS_ANALYZER_STRICT", None)

        configure_analyzer_policy_hook(_make_args("safe"))
        cmd_safe = os.environ.get("FLEX_HEADLESS_ANALYZER_CMD", "")
        assert "--policy safe" in cmd_safe
        assert os.environ.get("FLEX_HEADLESS_ANALYZER_STRICT") == "false"

        os.environ.pop("FLEX_HEADLESS_ANALYZER_CMD", None)
        os.environ.pop("FLEX_HEADLESS_ANALYZER_STRICT", None)

        configure_analyzer_policy_hook(_make_args("strict"))
        cmd_strict = os.environ.get("FLEX_HEADLESS_ANALYZER_CMD", "")
        assert "--policy strict" in cmd_strict
        assert os.environ.get("FLEX_HEADLESS_ANALYZER_STRICT") == "true"

        os.environ.pop("FLEX_HEADLESS_ANALYZER_CMD", None)
        os.environ.pop("FLEX_HEADLESS_ANALYZER_STRICT", None)

        configure_analyzer_policy_hook(_make_args("off"))
        assert os.environ.get("FLEX_HEADLESS_ANALYZER_CMD") is None

        print("smoke_main_analyzer_policy_wiring: PASS")

    finally:
        if original_cmd is None:
            os.environ.pop("FLEX_HEADLESS_ANALYZER_CMD", None)
        else:
            os.environ["FLEX_HEADLESS_ANALYZER_CMD"] = original_cmd

        if original_strict is None:
            os.environ.pop("FLEX_HEADLESS_ANALYZER_STRICT", None)
        else:
            os.environ["FLEX_HEADLESS_ANALYZER_STRICT"] = original_strict


if __name__ == "__main__":
    main()
