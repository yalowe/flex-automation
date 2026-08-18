from __future__ import annotations

from pathlib import Path
import subprocess

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
MAIN = REPO_ROOT / "main.py"


def _run(*args: str) -> str:
    cmd = [str(PYTHON), str(MAIN), *args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    text = (result.stdout or "") + (result.stderr or "")
    assert result.returncode == 0, text
    return text


def main() -> None:
    listed = _run("--list-analyzer-profiles")
    assert "ANALYZER PROFILES" in listed, listed
    assert "spread7-strict" in listed, listed
    assert "spread7-strict-calc8-lab" in listed, listed

    explained = _run("--explain-analyzer-profile", "spread7-strict")
    assert "Requested Name   : spread7-strict" in explained, explained
    assert "Policy Map       : 7:strict,*:safe" in explained, explained

    explained_auto = _run("--explain-analyzer-profile", "auto")
    assert "Requested Name   : auto" in explained_auto, explained_auto
    assert "Resolved Name    : spread7-strict" in explained_auto, explained_auto

    print("smoke_list_explain_profiles: PASS")


if __name__ == "__main__":
    main()
