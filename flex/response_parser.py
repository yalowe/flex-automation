import re


class FlexResponseParser:
    @staticmethod
    def parse_io_map(text: str) -> dict[str, dict[int, float]]:
        valve_flows = {}
        dosing_channel_flows = {}

        pattern = r"Valve\s+(\d+)\s+\|\s+Yes\s+\|\s+\d+\s+\|\s+(\d+)"
        for valve_id, nominal_flow in re.findall(pattern, text):
            valve_flows[int(valve_id)] = int(nominal_flow) / 100000

        for line in text.splitlines():
            parts = [part.strip() for part in line.split("|")]
            if len(parts) < 5:
                continue

            match = re.match(r"Dosing CH\s+(\d+)", parts[1])
            if not match:
                continue

            try:
                nominal_flow = int(parts[4])
            except ValueError:
                nominal_flow = 0

            dosing_channel_flows[int(match.group(1))] = nominal_flow / 100

        return {
            "valve_flows": valve_flows,
            "dosing_channel_flows": dosing_channel_flows,
        }

    @staticmethod
    def parse_recipe(text: str, recipe_id: int):
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith(str(recipe_id)):
                continue

            channels = {}
            for channel_id, block in enumerate(line.split("||")[1:5], start=1):
                parts = [part.strip() for part in block.split("|")]
                if len(parts) < 4:
                    continue

                try:
                    amount = int(parts[3])
                except ValueError:
                    amount = None

                channels[channel_id] = {
                    "enabled": parts[2] == "Yes",
                    "method": parts[0] or None,
                    "units": parts[1] or None,
                    "amount": amount,
                }

            return {"recipe_id": recipe_id, "channels": channels}

        return None

    @staticmethod
    def _decode_valve_mask(mask_text: str) -> list[int]:
        mask_text = (mask_text or "").strip()
        if not mask_text:
            return []

        try:
            mask_value = int(mask_text, 16)
        except ValueError:
            return []

        valves = []
        bit_index = 0
        while mask_value:
            if mask_value & 1:
                valves.append(bit_index + 1)
            mask_value >>= 1
            bit_index += 1

        return valves

    @classmethod
    def parse_shift_program(cls, text: str, program_id: int):
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith(str(program_id)):
                continue

            recipe_amount_match = re.search(r"\|\|\s*(\d+)\s*\|\s*(\d+)\s*\|", line)
            recipe_id = int(recipe_amount_match.group(1))
            amount = int(recipe_amount_match.group(2))

            valves = []
            for valve_mask_text in re.findall(r"\|\s+([0-9A-Fa-f]+)\|\|", line):
                valves.extend(cls._decode_valve_mask(valve_mask_text))

            if not valves:
                valves = [int(value) for value in re.findall(r"\|\s+(\d+)\|\|", line)]

            return {
                "shift_id": 1,
                "recipe_id": recipe_id,
                "amount": amount,
                "valves": valves,
            }

        return None

    @staticmethod
    def _extract_int(block: str, label: str) -> int | None:
        match = re.search(rf"{label}\s*:\s*(-?\d+)", block, re.IGNORECASE)
        return int(match.group(1)) if match else None

    @staticmethod
    def _extract_text(block: str, label: str) -> str | None:
        match = re.search(rf"{label}\s*:\s*([^\r\n|]+)", block, re.IGNORECASE)
        if not match:
            return None

        value = match.group(1).strip()
        return value or None

    @classmethod
    def parse_dosing_channels(cls, report: str):
        channels = {}
        blocks = re.finditer(
            r"Dosing\s+Channel:\s*(\d+)\s*,?(.*?)(?=Dosing\s+Channel:\s*\d+\s*,?|\Z)",
            report,
            re.IGNORECASE | re.DOTALL,
        )

        for block_match in blocks:
            channel_id = int(block_match.group(1))
            block = block_match.group(2)
            plan_amount = cls._extract_int(block, "Plan amount")
            flow = cls._extract_int(block, "Flow")
            delivered_quantity = cls._extract_int(block, "delivered quantity")
            delivered_time = cls._extract_int(block, "delivered time")
            remain_quantity = cls._extract_int(block, "remain quantity")
            remain_time = cls._extract_int(block, "remain time")

            if None in {
                plan_amount,
                flow,
                delivered_quantity,
                delivered_time,
                remain_quantity,
                remain_time,
            }:
                continue

            channels[channel_id] = {
                "plan_amount": plan_amount,
                "method": cls._extract_text(block, "Method"),
                "units": cls._extract_text(block, "Units"),
                "flow": flow,
                "delivered_quantity": delivered_quantity,
                "delivered_time": delivered_time,
                "remain_quantity": remain_quantity,
                "remain_time": remain_time,
            }

        return channels

    @classmethod
    def parse_live_report(cls, report: str) -> dict:
        irrigation_match = re.search(
            r"Irrigation Data:\s+Actual started time:.*?"
            r"Flow:\s*(-?\d+).*?"
            r"delivered quantity:\s*(\d+).*?"
            r"delivered time:\s*(\d+)",
            report,
            re.IGNORECASE | re.DOTALL,
        )
        dosing_channels = cls.parse_dosing_channels(report)
        if not irrigation_match:
            return {
                "irrigation_flow_raw": None,
                "water_delivered": None,
                "water_time": None,
                "dosing_channels": dosing_channels,
            }

        return {
            "irrigation_flow_raw": int(irrigation_match.group(1)),
            "water_delivered": int(irrigation_match.group(2)),
            "water_time": int(irrigation_match.group(3)),
            "dosing_channels": dosing_channels,
        }

    @classmethod
    def parse_completed_report(cls, report: str):
        water_match = re.search(
            r"Irrigation Data:\s+Actual started time:.*?"
            r"delivered quantity:\s*(\d+).*?"
            r"delivered time:\s*(\d+)",
            report,
            re.IGNORECASE | re.DOTALL,
        )
        if not water_match:
            raise ValueError("Irrigation section not found in completed report")

        dosing_channels = cls.parse_dosing_channels(report)
        return {
            "water_delivered": int(water_match.group(1)),
            "water_time": int(water_match.group(2)),
            "dosing_delivered": sum(
                channel["delivered_quantity"]
                for channel in dosing_channels.values()
            ),
            "dosing_time": max(
                (channel["delivered_time"] for channel in dosing_channels.values()),
                default=0,
            ),
            "dosing_remaining": sum(
                channel["remain_quantity"]
                for channel in dosing_channels.values()
            ),
            "dosing_channels": dosing_channels,
        }

    @staticmethod
    def parse_finish_reason(report: str):
        match = re.search(r"Finish reason:\s*([^\r\n]+)", report, re.IGNORECASE)
        if not match:
            raise ValueError("Finish reason not found")
        return match.group(1).strip()

    @staticmethod
    def parse_actual_start_time(report: str) -> str | None:
        match = re.search(r"Actual started time:\s*([0-9:]+)", report, re.IGNORECASE)
        return match.group(1) if match else None

    @staticmethod
    def extract_completed_report(report: str) -> str:
        start = report.rfind("Report type: Completed")
        if start == -1:
            raise ValueError("Completed report not found")
        return report[start:]