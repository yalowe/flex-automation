from parsers.do_parser import DOParser
from parsers.shift_parser import ShiftParser

from calculators.flex_calculator import FlexCalculator
from parsers.recipe_parser import RecipeParser
from calculators.flex_device_model import DOSING_FLOWS


class FlexConfigService:

    def __init__(self, controller):
        self.controller = controller

    def get_valve_flows(self):

        result = self.controller.send("irrdomap info")

        return DOParser.parse(result.response)

    def shifts_info(self, program_id: int):

        result = self.controller.send("shift info")

        return ShiftParser.parse_program(result.response, program_id)

    def get_program_configuration(self, program_id):

        valve_flows = self.get_valve_flows()

        program = self.shifts_info(program_id)

        flow = FlexCalculator.flow_from_valves(
            program["valves"],
            valve_flows,
        )

        wm_cycle = FlexCalculator.wm_cycle_ms(flow)

        recipe_response = self.controller.send("recipe info")

        recipe = RecipeParser.parse_recipe(
            recipe_response.response,
            program["recipe_id"],
        )

        dosing_channels = {}

        for channel_id, channel in recipe["channels"].items():

            if not channel["enabled"]:
                continue

            dosing_flow = DOSING_FLOWS[channel_id]

            dosing_channels[channel_id] = {
                **channel,
                "flow": dosing_flow,
                "dm_cycle": FlexCalculator.dm_cycle_ms(dosing_flow),
            }

        return {
            "program_id": program_id,
            "recipe_id": program["recipe_id"],
            "valves": program["valves"],
            "flow": flow,
            "wm_cycle": wm_cycle,
            "dosing_channels": dosing_channels,
        }
