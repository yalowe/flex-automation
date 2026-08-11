from models.dosing_scenario import DosingScenario


BULK_TIME_TIME_PROGRAM = DosingScenario(
    name="Bulk By Time",
    program_id=3,
    wait_time_sec=243,
    expected_water=6000,
    expected_dosing=70,
    expected_remaining=0,
    water_tolerance_percent=10,
    dosing_tolerance_percent=10,
    remaining_tolerance_percent=5,
)

BULK_QUANTITY_TIME_PROGRAM = DosingScenario(
    name="Bulk By Quantity",
    program_id=1,
    wait_time_sec=183,
    expected_water=6000,
    expected_dosing=70,
    expected_remaining=0,
    water_tolerance_percent=10,
    dosing_tolerance_percent=10,
    remaining_tolerance_percent=5,
)

SPREAD_TIME_PROGRAM = DosingScenario(
    name="Spread By Time",
    program_id=2,
    wait_time_sec=183,
    expected_water=47000,
    expected_dosing=14500,
    expected_remaining=0,
    water_tolerance_percent=10,
    dosing_tolerance_percent=10,
    remaining_tolerance_percent=15,
)

PROPORTIONAL_PROGRAM = DosingScenario(
    name="Proportional",
    program_id=8,
    wait_time_sec=729,
    expected_water=1500,
    expected_dosing=0,
    expected_remaining=0,
    water_tolerance_percent=10,
    dosing_tolerance_percent=10,
    remaining_tolerance_percent=15,
)