from models.validation_result import ValidationResult


class QueueValidator:

    @staticmethod
    def validate(report: str) -> ValidationResult:

        queued_programs = []

        for line in report.splitlines():

            if "Irrigation program Id:" in line:
                queued_programs.append(line.strip())

        message = (
            "Queue contains:\n" + "\n".join(queued_programs)
            if queued_programs
            else "Queue is empty"
        )

        return ValidationResult(passed=True, message=message, is_info=True)
