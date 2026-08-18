from dataclasses import dataclass
from enum import Enum


class IrrigationCommand(Enum):
    SKIP_SHIFT = 2
    SKIP_PROGRAM = 3
    RUN_PROGRAM = 5


@dataclass
class CommandResult:
    command: str
    success: bool
    response: str


class IrrigationService:
    def __init__(self, controller):
        self.controller = controller

    def execute(self, command, program_id=1):
        return self.controller.send(f"IrrCmd Set {command.value} {program_id}")

    def skip_shift(self, program_id=1):
        return self.execute(IrrigationCommand.SKIP_SHIFT, program_id)

    def skip_program(self, program_id=1):
        return self.execute(IrrigationCommand.SKIP_PROGRAM, program_id)

    def run_program(self, program_id):
        return self.execute(IrrigationCommand.RUN_PROGRAM, program_id)

    def running_report(self, program_id: int):
        return self.controller.send(f"IrrRep Print 0 {program_id}")

    def completed_report(self, program_id: int):
        return self.controller.send(f"IrrRep Print 1 {program_id}")

    def programs_info(self):
        return self.controller.send("IrrProg Info")