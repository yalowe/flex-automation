from enum import Enum


class IrrigationCommand(Enum):
    SKIP_SHIFT = 2
    SKIP_PROGRAM = 3
    RUN_PROGRAM = 5