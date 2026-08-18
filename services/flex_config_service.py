from parsers.do_parser import DOParser
from parsers.shift_parser import ShiftParser

from calculators.flex_calculator import FlexCalculator
from parsers.recipe_parser import RecipeParser
from services.flex_gui_service import load_wm_settings
import re
from pathlib import Path


class FlexConfigService:

    def __init__(self, controller, wm_settings_path: str | Path | None = None):
        self.controller = controller
        self.wm_settings_path = wm_settings_path or (
            Path(__file__).resolve().parents[1] / "Flex_tester" / "wm_settings.json"
        )

    def io_map_info(self):
        result = self.controller.send("irrdomap info")
        return DOParser.parse_io_map(result.response)

    def shifts_info(self, program_id: int):

        result = self.controller.send("shift info")

        return ShiftParser.parse_program(result.response, program_id)

    def program_info(self, program_id: int):

        result = self.controller.send("IrrProg Info")

        for line in result.response.splitlines():
            row_match = re.match(r"\s*(\d+)\|", line)

            if not row_match:
                continue

            if int(row_match.group(1)) != program_id:
                continue

            parts = [part.strip() for part in line.split("|")]

            return {
                "program_type": parts[1] if len(parts) > 1 else None,
                "program_depth": (parts[3] if len(parts) > 3 else "").strip().lower()
                == "yes",
                "program_units": parts[5] if len(parts) > 5 else None,
                "water_before": self._safe_int(parts[6]) if len(parts) > 6 else 0,
                "water_after": self._safe_int(parts[7]) if len(parts) > 7 else 0,
            }

        return {
            "program_type": None,
            "program_depth": False,
            "program_units": None,
            "water_before": 0,
            "water_after": 0,
        }

    def di_map_info(self):

        result = self.controller.send("IrrDIMap Info")

        water_meter_rate = None
        dosing_meter_rates = {}

        for line in result.response.splitlines():
            parts = [part.strip() for part in line.split("|")]

            if len(parts) < 5:
                continue

            device_name = parts[1] if len(parts) > 1 else ""
            rate = self._safe_int(parts[4]) if len(parts) > 4 else 0

            if device_name == "Main WaterMeter":
                water_meter_rate = rate
                continue

            meter_match = re.match(r"Dosing Meter\s+(\d+)", device_name)
            if meter_match:
                dosing_meter_rates[int(meter_match.group(1))] = rate

        return {
            "water_meter_rate": water_meter_rate,
            "dosing_meter_rates": dosing_meter_rates,
        }

    def get_program_configuration(self, program_id):
        io_map = self.io_map_info()
        valve_flows = io_map["valve_flows"]
        dosing_channel_flows = io_map["dosing_channel_flows"]

        program = self.shifts_info(program_id)
        program_info = self.program_info(program_id)
        di_map_info = self.di_map_info()
        wm_settings = load_wm_settings(self.wm_settings_path)
        dm_liters_per_pulse = self._positive_float(
            wm_settings.get("dm_liters_per_pulse"),
            default=1.0,
        )

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

            dosing_flow = dosing_channel_flows.get(channel_id, 0)

            dosing_channels[channel_id] = {
                **channel,
                "flow": dosing_flow,
                "dm_cycle": FlexCalculator.dm_cycle_ms(
                    dosing_flow,
                    dm_liters_per_pulse,
                ),
                "dm_rate": di_map_info["dosing_meter_rates"].get(channel_id),
                "dm_liters_per_pulse": dm_liters_per_pulse,
            }

        return {
            "program_id": program_id,
            "shift_id": program["shift_id"],
            "recipe_id": program["recipe_id"],
            "program_type": program_info["program_type"],
            "program_depth": program_info["program_depth"],
            "program_units": program_info["program_units"],
            "water_before": program_info["water_before"],
            "water_after": program_info["water_after"],
            "shift_amount": program["amount"],
            "valves": program["valves"],
            "flow": flow,
            "water_meter_rate": di_map_info["water_meter_rate"],
            "water_meter_pulse_liters": self._wm_pulse_size_liters(
                di_map_info["water_meter_rate"]
            ),
            "wm_cycle": wm_cycle,
            "dosing_channels": dosing_channels,
        }

    @staticmethod
    def _safe_int(value):

        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _positive_float(value, default):

        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return default

        return parsed if parsed > 0 else default

    @staticmethod
    def _wm_pulse_size_liters(rate):

        if not rate:
            return None

        return 1000 / rate
