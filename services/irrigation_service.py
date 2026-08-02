from flex.commands import IrrigationCommand


class IrrigationService:

    def __init__(self, controller):
        self.controller = controller

    def execute(self, command, program_id=1):
        return self.controller.send(f"IrrCmd Set {command.value} {program_id}")

    def pause(self, program_id=1):
        return self.execute(IrrigationCommand.PAUSE_ML, program_id)

    def resume(self, program_id=1):
        return self.execute(IrrigationCommand.RESUME_ML, program_id)

    def skip_shift(self, program_id=1):
        return self.execute(IrrigationCommand.SKIP_SHIFT, program_id)

    def skip_program(self, program_id=1):
        return self.execute(IrrigationCommand.SKIP_PROGRAM, program_id)

    def run_program(self, program_id):
        return self.execute(IrrigationCommand.RUN_PROGRAM, program_id)

    def complete(self, program_id=1):
        return self.execute(IrrigationCommand.COMPLETE, program_id)

    def stop_dosing(self, program_id=1):
        return self.execute(IrrigationCommand.MANUAL_WAIT, program_id)

    def start_over(self, program_id=1):
        return self.execute(IrrigationCommand.RUN_PROGRAM, program_id)


    def running_report(self, program_id: int):
        return self.controller.send(
            f"IrrRep Print 0 {program_id}"
        )

    def completed_report(self, program_id: int):
        return self.controller.send(
            f"IrrRep Print 1 {program_id}"
        )

    def uncompleted_report(self):
        return self.controller.send(
            "Uncomplt RepGet"
        )

    def programs_info(self):
        return self.controller.send("IrrProg Info")

    def shifts_info(self):
        return self.controller.send("shift info")

    def recipes_info(self):
        return self.controller.send("Recipe Info")        