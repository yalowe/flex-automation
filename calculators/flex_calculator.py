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
    def dm_cycle_ms(flow_lph: float, liters_per_pulse: float = 1.0) -> float:

        if flow_lph <= 0 or liters_per_pulse <= 0:
            return 0

        return round((liters_per_pulse * 3600000) / flow_lph, 2)

    @staticmethod
    def total_irrigation_flow(flows_m3h: list[float]) -> float:
        return sum(flows_m3h)

    @staticmethod
    def flow_from_valves(valves: list[int], valve_flows: dict[int, float]) -> float:

        total = 0.0

        for valve in valves:
            total += valve_flows.get(valve, 0.0)

        return total
