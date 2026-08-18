from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import main as runner_main


def main() -> None:
    missing_file = REPO_ROOT / "config" / "__missing_analyzer_profiles__.json"
    profiles = runner_main.load_analyzer_profiles(str(missing_file))

    assert "off" in profiles
    assert "spread7-strict" in profiles
    assert profiles["spread7-strict"]["policy_map"] == "7:strict,*:safe"

    print("smoke_analyzer_profiles_file_fallback: PASS")


if __name__ == "__main__":
    main()
