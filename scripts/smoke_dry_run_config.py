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
        "--analyzer-profile",
        "auto",
        "--dry-run-config",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    text = (result.stdout or "") + (result.stderr or "")
    assert result.returncode == 0, text
    assert "========== EFFECTIVE CONFIG ==========" in text, text
    assert "Analyzer Profile      : spread7-strict-calc8-lab" in text, text
    assert "Analyzer Policy Map   : 7:strict,8:lab,*:safe" in text, text
    assert "Active Scenarios       : Bulk By Time - Time#1" in text, text

    print("smoke_dry_run_config: PASS")


if __name__ == "__main__":
    main()
