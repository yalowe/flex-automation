from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from models.dosing_scenario import DosingScenario
from tests.programs_and_dosings_validation import validate_results_from_controller


def main() -> None:
    scenario = DosingScenario(name="Spread By Quantity", program_id=7)

    config_data = {
        "program_id": 7,
        "program_units": "Quant",
        "flow": 0.9,
        "dosing_channels": {
            1: {
                "enabled": True,
                "method": "Spread",
                "units": "Quantity",
                "amount": 200,
                "flow": 300.0,
                "dm_rate": 10,
            }
        },
    }

    expectations = {
        "inconsistencies": [],
        "expected_water_report_units": None,
        "expected_dosing_report_units": None,
        "expected_plan_report_units": None,
    }

    data = {
        "water_delivered": 100,
        "water_time": 10,
        "dosing_delivered": 150,
        "dosing_time": 50,
        "dosing_remaining": 25,
    }

    actual_dosing_channels = {
        1: {
            "plan_amount": 200,
            "method": "Spread",
            "units": "Quantity",
            "flow": 30070,
            "delivered_quantity": 150,
            "delivered_time": 50,
            "remain_quantity": 25,
            "remain_time": 7,
        }
    }

    validate_results_from_controller(
        config_data=config_data,
        expectations=expectations,
        data=data,
        scenario=scenario,
        actual_dosing_channels=actual_dosing_channels,
    )

    print("smoke_program7_validation: PASS")


if __name__ == "__main__":
    main()
