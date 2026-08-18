import re


class ReportParser:

    @staticmethod
    def _extract_int(block: str, label: str) -> int | None:
        match = re.search(rf"{label}\s*:\s*(-?\d+)", block, re.IGNORECASE)
        if not match:
            return None

        return int(match.group(1))

    @staticmethod
    def _extract_text(block: str, label: str) -> str | None:
        match = re.search(rf"{label}\s*:\s*([^\r\n|]+)", block, re.IGNORECASE)
        if not match:
            return None

        value = match.group(1).strip()
        return value or None

    @staticmethod
    def parse_dosing_channels(report: str):
        channels = {}

        channel_blocks = re.finditer(
            r"Dosing\s+Channel:\s*(\d+)\s*,?(.*?)(?=Dosing\s+Channel:\s*\d+\s*,?|\Z)",
            report,
            re.IGNORECASE | re.DOTALL,
        )

        for block_match in channel_blocks:
            channel_id = int(block_match.group(1))
            block = block_match.group(2)

            plan_amount = ReportParser._extract_int(block, "Plan amount")
            flow = ReportParser._extract_int(block, "Flow")
            delivered_quantity = ReportParser._extract_int(block, "delivered quantity")
            delivered_time = ReportParser._extract_int(block, "delivered time")
            remain_quantity = ReportParser._extract_int(block, "remain quantity")
            remain_time = ReportParser._extract_int(block, "remain time")

            if (
                plan_amount is None
                or flow is None
                or delivered_quantity is None
                or delivered_time is None
                or remain_quantity is None
                or remain_time is None
            ):
                continue

            channels[channel_id] = {
                "plan_amount": plan_amount,
                "method": ReportParser._extract_text(block, "Method"),
                "units": ReportParser._extract_text(block, "Units"),
                "flow": flow,
                "delivered_quantity": delivered_quantity,
                "delivered_time": delivered_time,
                "remain_quantity": remain_quantity,
                "remain_time": remain_time,
            }

        return channels

    @staticmethod
    def parse_completed_report(report: str):

        water_match = re.search(
            r"Irrigation Data:\s+Actual started time:.*?"
            r"delivered quantity:\s*(\d+).*?"
            r"delivered time:\s*(\d+)",
            report,
            re.IGNORECASE | re.DOTALL,
        )

        if not water_match:
            raise ValueError("Irrigation section not found in completed report")

        dosing_channels = ReportParser.parse_dosing_channels(report)
        total_dosing = sum(
            channel["delivered_quantity"] for channel in dosing_channels.values()
        )
        total_remaining = sum(
            channel["remain_quantity"] for channel in dosing_channels.values()
        )
        max_dosing_time = max(
            (channel["delivered_time"] for channel in dosing_channels.values()),
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
            r"Finish reason:\s*([^\r\n]+)",
            report,
            re.IGNORECASE,
        )

        if not match:
            raise ValueError("Finish reason not found")

        return match.group(1).strip()

    @staticmethod
    def parse_actual_start_time(report: str) -> str | None:

        match = re.search(r"Actual started time:\s*([0-9:]+)", report, re.IGNORECASE)

        if not match:
            return None

        return match.group(1)

    _last_report = None

    @staticmethod
    def extract_completed_report(report: str) -> str:
        start = report.rfind("Report type: Completed")

        if start == -1:
            raise ValueError("Completed report not found")

        extracted = report[start:]
        if extracted != ReportParser._last_report:
            ReportParser._last_report = extracted

        return extracted
