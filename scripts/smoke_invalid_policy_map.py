from __future__ import annotations

from pathlib import Path
import subprocess

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
MAIN = REPO_ROOT / "main.py"


def main() -> None:
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

    print("smoke_invalid_policy_map: PASS")


if __name__ == "__main__":
    main()
