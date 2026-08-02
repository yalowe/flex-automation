import time


class ProgramTests:

    def __init__(self, irrigation):
        self.irrigation = irrigation

    def test_run_program(self, program_id=3):

        result = self.irrigation.run_program(program_id)

        assert result.success, result.response

        print("Program started successfully")

        time.sleep(120)

        report = self.irrigation.uncompleted_report()

        assert report.success, report.response

        print(report.response)


    def test_skip_shift(self, program_id=3):
            self.test_run_program(program_id)

            result = self.irrigation.skip_shift(program_id)
            time.sleep(1)

            assert result.success, result.response


    def test_pause_program(self, program_id=3):
        self.test_run_program(program_id)

        result = self.irrigation.pause(program_id)
        time.sleep(1)

        assert result.success, result.response

    
    def test_resume_program(self, program_id=3):
        self.test_run_program(program_id)
        time.sleep(10)

        self.irrigation.pause(program_id)
        time.sleep(10)

        result = self.irrigation.resume(program_id)

        assert result.success, result.response

   

    def test_skip_program(self, program_id=3):
        self.test_run_program(program_id)
        time.sleep(10)

        result = self.irrigation.skip_program(program_id)

        assert result.success, result.response

    def test_complete(self, program_id=3):

        result = self.irrigation.complete(program_id)

        assert result.success, result.response

    def test_start_over(self, program_id=3):

        result = self.irrigation.start_over(program_id)

        assert result.success, result.response