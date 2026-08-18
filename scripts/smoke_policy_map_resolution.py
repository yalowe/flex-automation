from __future__ import annotations

from pathlib import Path
import os
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.programs_and_dosings import _resolve_analyzer_policy_for_program


def main() -> None:
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

        print("smoke_policy_map_resolution: PASS")

    finally:
        if orig_map is None:
            os.environ.pop("FLEX_HEADLESS_ANALYZER_POLICY_MAP", None)
        else:
            os.environ["FLEX_HEADLESS_ANALYZER_POLICY_MAP"] = orig_map

        if orig_default is None:
            os.environ.pop("FLEX_HEADLESS_ANALYZER_DEFAULT_POLICY", None)
        else:
            os.environ["FLEX_HEADLESS_ANALYZER_DEFAULT_POLICY"] = orig_default


if __name__ == "__main__":
    main()
