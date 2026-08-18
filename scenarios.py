from models.dosing_scenario import DosingScenario

BULK_TIME_TIME_PROGRAM = DosingScenario(
    name="Bulk By Time - Time",
    program_id=1,
)

BULK_TIME_QUANTITY_PROGRAM = DosingScenario(
    name="Bulk By Time - Quantity",
    program_id=2,
)

BULK_TIME_DEPTH_PROGRAM = DosingScenario(
    name="Bulk By Time - Depth",
    program_id=3,
)

BULK_QUANTITY_TIME_PROGRAM = DosingScenario(
    name="Bulk By Quantity - Time",
    program_id=4,
)

BULK_QUANTITY_QUANTITY_PROGRAM = DosingScenario(
    name="Bulk By Quantity - Quantity",
    program_id=5,
)

SPREAD_TIME_PROGRAM = DosingScenario(
    name="Spread By Time",
    program_id=6,
)

SPREAD_TIME_TIME_PROGRAM = SPREAD_TIME_PROGRAM

SPREAD_QUANTITY_PROGRAM = DosingScenario(
    name="Spread By Quantity",
    program_id=7,
)

SPREAD_QUANTITY_QUANTITY_PROGRAM = SPREAD_QUANTITY_PROGRAM

CALCULATED_QUANTITY_PROGRAM = DosingScenario(
    name="Calculated Quantity",
    program_id=8,
)
