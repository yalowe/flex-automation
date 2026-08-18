import re


class DOParser:

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