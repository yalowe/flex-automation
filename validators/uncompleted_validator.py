from models.validation_result import ValidationResult


class UncompletedValidator:

    @staticmethod
    def validate(report: str) -> ValidationResult:

        passed = "Number of programs data: 0" in report

        return ValidationResult(
            passed=passed,
            message="No uncompleted programs found"
            if passed
            else "Uncompleted programs detected"
        )