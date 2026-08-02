import re


class ReportParser:

    @staticmethod
    def parse_completed_report(report: str):

        water_match = re.search(
            r"Irrigation Data:\s+Actual started time:.*?"
            r"delivered quantity:\s*(\d+).*?"
            r"delivered time:\s*(\d+)",
            report,
            re.DOTALL,
        )

        dosing_matches = re.findall(
            r"Dosing Channel:\s*\d+.*?delivered quantity:\s*(\d+).*?delivered time:\s*(\d+).*?remain quantity:\s*(\d+)",
            report,
            re.DOTALL,
        )

        total_dosing = sum(int(match[0]) for match in dosing_matches)

        total_remaining = sum(int(match[2]) for match in dosing_matches)

        max_dosing_time = max(
            (int(match[1]) for match in dosing_matches),
            default=0,
        )

        return {
            "water_delivered": int(water_match.group(1)),
            "water_time": int(water_match.group(2)),
            "dosing_delivered": total_dosing,
            "dosing_time": max_dosing_time,
            "dosing_remaining": total_remaining,
        }

    @staticmethod
    def parse_finish_reason(report: str):

        match = re.search(
            r"Finish reason:\s*(\w+)",
            report,
        )

        if not match:
            raise ValueError("Finish reason not found")

        return match.group(1)

    @staticmethod
    def parse_actual_start_time(report: str) -> str | None:

        match = re.search(
            r"Actual started time:\s*([0-9:]+)",
            report,
        )

        if not match:
            return None

        return match.group(1)

    @staticmethod
    def extract_completed_report(report: str) -> str:

        start = report.rfind("Report type: Completed")

        if start == -1:
            raise ValueError(
                "Completed report not found"
            )

        return report[start:]
