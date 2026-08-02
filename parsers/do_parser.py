import re


def flow_from_nominal(nom_flow: int) -> float:
    return nom_flow / 100000


class DOParser:

    @staticmethod
    def parse(text: str) -> dict[int, float]:

        valves = {}

        pattern = r"Valve\s+(\d+)\s+\|\s+Yes\s+\|\s+\d+\s+\|\s+(\d+)"

        for valve_id, nominal_flow in re.findall(pattern, text):

            valves[int(valve_id)] = flow_from_nominal(
                int(nominal_flow)
            )

        return valves