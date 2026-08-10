from flex.commands import IrrigationCommand


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
        return self.controller.send(
            f"IrrRep Print 0 {program_id}"
        )

    def completed_report(self, program_id: int):
        return self.controller.send(
            f"IrrRep Print 1 {program_id}"
        )

    def programs_info(self):
        return self.controller.send("IrrProg Info")

    def shifts_info(self):
        return self.controller.send("shift info")

    def recipes_info(self):
        return self.controller.send("Recipe Info")        