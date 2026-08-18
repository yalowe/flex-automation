from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.expectation_builder import ExpectationBuilder


def main() -> None:
    config_data = {
        "program_units": "Quant",
        "program_depth": False,
        "shift_amount": 45000,
        "flow": 0.9,
        "water_before": 4000,
        "water_after": 4000,
        "dosing_channels": {
            1: {
                "enabled": True,
                "method": "Spread",
                "units": "Time",
                "amount": 7,
                "flow": 21.0,
                "dm_rate": 10,
            }
        },
    }

    expectations = ExpectationBuilder.build(config_data)
    channel = expectations["channel_expectations"][1]

    assert channel["spread_schedule"]["delivered_time_seconds"] == 420
    assert channel["expected_report_units"] == 245
    assert expectations["expected_dosing_report_units"] == 245
    assert expectations["expected_plan_report_units"] == 245

    print("smoke_spread_time_expectation: PASS")


if __name__ == "__main__":
    main()