from calculators.flex_device_model import VALVE_FLOWS
class FlexCalculator:

    @staticmethod
    def flow_from_nominal(nom_flow: int) -> float:
        return nom_flow / 100000

    @staticmethod
    def wm_cycle_ms(flow_m3h: float) -> int:

        if flow_m3h <= 0:
            return 0

        flow_lph = flow_m3h * 1000

        return round(3600000 / flow_lph)

    @staticmethod
    def dm_cycle_ms(flow_lph: float) -> int:

        if flow_lph <= 0:
            return 0

        return round(3600000 / flow_lph)

    @staticmethod
    def total_irrigation_flow(flows_m3h: list[float]) -> float:
        return sum(flows_m3h)

    @staticmethod
    def program_flow(valves: list[int]) -> float:

        total = 0

        for valve in valves:
            total += VALVE_FLOWS[valve]
        return total

    @staticmethod
    def flow_from_valves(
            valves: list[int],
            valve_flows: dict[int, float]
    ) -> float:

        total = 0

        for valve in valves:
            total += valve_flows[valve]

        return total