from dataclasses import dataclass


@dataclass
class DosingScenario:
    name: str
    program_id: int

    expected_water: int | None = None
    expected_dosing: int | None = None
    expected_remaining: int | None = None
    expected_plan_amount: int | None = None

    water_tolerance_percent: int = 10
    dosing_tolerance_percent: int = 10
    remaining_tolerance_percent: int = 5