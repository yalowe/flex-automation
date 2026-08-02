from enum import Enum


class IrrigationCommand(Enum):
    PAUSE_ML = 0
    RESUME_ML = 1
    SKIP_SHIFT = 2
    SKIP_PROGRAM = 3
    MANUAL_WAIT = 4
    RUN_PROGRAM = 5
    COMPLETE = 6