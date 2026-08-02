from models.validation_result import ValidationResult


class ProgramFinishedValidator:

    @staticmethod
    def validate(uncompleted_report: str) -> ValidationResult:

        passed = "Number of programs data: 0" in uncompleted_report

        return ValidationResult(
            passed=passed,
            message="Program finished successfully"
            if passed
            else "Program did not finish"
        )