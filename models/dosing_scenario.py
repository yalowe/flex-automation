from dataclasses import dataclass


@dataclass
class DosingScenario:

    name: str
    program_id: int
    wait_time_sec: int
    expected_water: int
    expected_dosing: int
    expected_remaining: int = 0
    water_tolerance_percent: int = 10
    dosing_tolerance_percent: int = 10
    remaining_tolerance_percent: int = 5
    expected_plan_amount: int | None = None