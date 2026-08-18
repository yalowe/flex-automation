from __future__ import annotations

from pathlib import Path
import json
import shutil
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import main as runner_main

TMP_DIR = REPO_ROOT / "config" / "_smoke_invalid_profiles"
TMP_FILE = TMP_DIR / "analyzer_profiles_invalid.json"


def main() -> None:
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    bad_profiles = {
        "bad-profile": {
            "policy": "safe",
            "policy_map": "7-strict,*:safe",
            "default_policy": "safe",
        }
    }
    TMP_FILE.write_text(json.dumps(bad_profiles, indent=2), encoding="utf-8")

    try:
        runner_main.load_analyzer_profiles(str(TMP_FILE))
    except RuntimeError as exc:
        text = str(exc)
        assert "Invalid analyzer profile 'bad-profile'" in text, text
        assert "Expected format <program_id>:<policy> or *:<policy>" in text, text
        print("smoke_invalid_analyzer_profiles_file: PASS")
        return

    raise AssertionError("Expected invalid analyzer profiles file to fail")


if __name__ == "__main__":
    main()
