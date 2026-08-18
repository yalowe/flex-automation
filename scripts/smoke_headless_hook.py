from pathlib import Path
import os
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.programs_and_dosings import _run_headless_analyzer_hook


def main() -> None:
    os.environ["FLEX_HEADLESS_ANALYZER_CMD"] = (
        "python -c \"print('hook-ok scenario={scenario_name} program={program_id} anomalies={anomaly_count}')\""
    )

    ok, error = _run_headless_analyzer_hook(
        scenario_name="Spread By Quantity",
        program_id=7,
        session_dir="logs/20260817_000000",
        anomaly_count=0,
    )

    assert ok, f"Headless hook should pass, got: {error}"
    print("smoke_headless_hook: PASS")


if __name__ == "__main__":
    main()
