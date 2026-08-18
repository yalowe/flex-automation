"""Dynamic expectation builder for controller-discovered irrigation configuration.

Future configuration-write extension points (not implemented here):
- services/flex_config_service.py::FlexConfigService.get_program_configuration
  controller command: "IrrProg Info", "shift info", "recipe info", "IrrDIMap Info", "irrdomap info"
  supported configuration: valve flow rate, shift flow, water before, water after,
  water meter configuration, dosing meter configuration, dosing channel nominal flow,
  recipe configuration
- flex/controller.py::FlexController.send
  controller command: firmware write commands such as "Recipe Config", "Recipe Reset",
  "PR set", "DO Config", "AI Config", "DI Config", "IrrDO Mode"
  supported configuration: recipe config, parameter writes, digital output config,
  analog input config, water meter or dosing meter configuration, valve config,
  proportional ratio, calculated quantity, dosing channel nominal flow
- services/irrigation_service.py::IrrigationService.*
  controller command: "IrrCmd Set ...", "IrrRep Print ..."
  supported configuration: runtime program execution state only; no write paths for
  controller configuration are implemented in this project yet
"""

import math


class ExpectationBuilder:
    """Build expected controller behavior from runtime-discovered config."""

    WATER_REPORT_UNITS_PER_LITER = 100

    @staticmethod
    def _is_quantity_unit(unit_value) -> bool:
        return (unit_value or "").strip().lower() in {
            "quant",
            "qty",
            "quantity",
            "depth",
        }

    @staticmethod
    def _is_time_unit(unit_value) -> bool:
        return (unit_value or "").strip().lower() == "time"

    @classmethod
    def build(cls, config_data: dict) -> dict:
        flow_m3h = config_data.get("flow", 0)
        flow_lph = flow_m3h * 1000
        shift_amount = config_data.get("shift_amount", 0)
        program_units = (config_data.get("program_units") or "").strip().lower()
        program_depth = bool(config_data.get("program_depth"))
        water_before = config_data.get("water_before", 0)
        water_after = config_data.get("water_after", 0)

        runtime_minutes = None
        expected_water_report_units = None
        expected_water_liters = None

        if cls._is_time_unit(program_units) and shift_amount > 0:
            runtime_minutes = shift_amount
            expected_water_liters = flow_lph * (runtime_minutes / 60)
            expected_water_report_units = cls.water_report_units_from_liters(
                expected_water_liters
            )
        elif cls._is_quantity_unit(program_units) and shift_amount > 0:
            expected_water_report_units = shift_amount
            expected_water_liters = (
                expected_water_report_units / cls.WATER_REPORT_UNITS_PER_LITER
            )
            if flow_lph > 0:
                runtime_minutes = (expected_water_liters / flow_lph) * 60
            else:
                runtime_minutes = None

        dosing_window_minutes = None
        if runtime_minutes is not None:
            dosing_window_minutes = runtime_minutes
            if cls._is_time_unit(program_units):
                dosing_window_minutes = max(
                    runtime_minutes - water_before - water_after,
                    0,
                )
            if cls._is_quantity_unit(program_units) and flow_lph > 0:
                water_before_liters = water_before / cls.WATER_REPORT_UNITS_PER_LITER
                water_after_liters = water_after / cls.WATER_REPORT_UNITS_PER_LITER
                water_before_runtime_minutes = (water_before_liters / flow_lph) * 60
                water_after_runtime_minutes = (water_after_liters / flow_lph) * 60
                dosing_window_minutes = max(
                    runtime_minutes
                    - water_before_runtime_minutes
                    - water_after_runtime_minutes,
                    0,
                )

            if program_depth and dosing_window_minutes is not None:
                dosing_window_minutes = math.floor(dosing_window_minutes)

        expected_dosing_report_units = 0
        expected_plan_report_units = 0
        has_supported_dosing_expectation = False
        channel_expectations = {}

        for channel_id, channel in sorted(
            config_data.get("dosing_channels", {}).items()
        ):
            if not channel.get("enabled"):
                continue

            channel_expectation = cls._build_channel_expectation(
                channel_id=channel_id,
                channel=channel,
                dosing_window_minutes=dosing_window_minutes,
                runtime_minutes=runtime_minutes,
                expected_water_liters=expected_water_liters,
                flow_lph=flow_lph,
                wm_pulse_size_liters=config_data.get("water_meter_pulse_liters"),
                program_units=program_units,
            )
            channel_expectations[channel_id] = channel_expectation

            expected_value = channel_expectation.get("expected_report_units")
            if expected_value is not None:
                expected_dosing_report_units += expected_value
                expected_plan_report_units += expected_value
                has_supported_dosing_expectation = True

        inconsistencies = cls.find_inconsistencies(
            config_data=config_data,
            expectations={
                "runtime_minutes": runtime_minutes,
                "expected_water_report_units": expected_water_report_units,
                "expected_water_liters": expected_water_liters,
                "expected_dosing_report_units": expected_dosing_report_units,
                "expected_plan_report_units": expected_plan_report_units,
            },
        )

        return {
            "runtime_minutes": runtime_minutes,
            "dosing_window_minutes": dosing_window_minutes,
            "expected_water_report_units": expected_water_report_units,
            "expected_water_liters": expected_water_liters,
            "expected_dosing_report_units": (
                expected_dosing_report_units
                if has_supported_dosing_expectation
                else None
            ),
            "expected_plan_report_units": (
                expected_plan_report_units if has_supported_dosing_expectation else None
            ),
            "wm_cycle_ms": config_data.get("wm_cycle"),
            "water_meter_rate": config_data.get("water_meter_rate"),
            "water_meter_pulse_liters": config_data.get("water_meter_pulse_liters"),
            "channel_expectations": channel_expectations,
            "inconsistencies": inconsistencies,
        }

    @classmethod
    def _build_channel_expectation(
        cls,
        channel_id: int,
        channel: dict,
        dosing_window_minutes,
        runtime_minutes,
        expected_water_liters,
        flow_lph,
        wm_pulse_size_liters,
        program_units,
    ) -> dict:
        method = (channel.get("method") or "").strip().lower()
        units = (channel.get("units") or "").strip().lower()
        amount = channel.get("amount")
        dosing_flow_lph = channel.get("flow", 0)

        expected_report_units = None
        ratio_l_per_m3 = None
        pulse_interval_sec = None
        pulse_interval_reason = None
        spread_schedule = None

        if method == "bulk" and amount is not None:
            if cls._is_time_unit(units):
                configured_runtime_minutes = float(amount)
                effective_runtime_minutes = dosing_window_minutes
                if effective_runtime_minutes is None:
                    effective_runtime_minutes = runtime_minutes

                if effective_runtime_minutes is not None:
                    actual_runtime_minutes = min(
                        configured_runtime_minutes,
                        effective_runtime_minutes,
                    )
                else:
                    actual_runtime_minutes = configured_runtime_minutes

                expected_liters = dosing_flow_lph * (actual_runtime_minutes / 60)
                expected_report_units = cls.dosing_report_units_from_liters(
                    expected_liters
                )
            elif cls._is_quantity_unit(units) or cls._is_quantity_unit(program_units):
                if (
                    method == "bulk"
                    and dosing_window_minutes is not None
                    and dosing_window_minutes <= 0
                ):
                    expected_report_units = 0
                else:
                    expected_report_units = amount
        elif method == "spread" and amount is not None:
            if cls._is_time_unit(units):
                spread_schedule = cls._spread_time_schedule(
                    configured_amount_minutes=float(amount),
                    dosing_window_minutes=dosing_window_minutes,
                    min_on_delay_sec=channel.get("min_on_delay_sec", 10),
                    min_off_delay_sec=channel.get("min_off_delay_sec", 10),
                )
                delivered_time_seconds = spread_schedule["delivered_time_seconds"]
                expected_liters = dosing_flow_lph * delivered_time_seconds / 3600
                expected_report_units = cls.dosing_report_units_from_liters(
                    expected_liters
                )
            elif cls._is_quantity_unit(units) or cls._is_quantity_unit(program_units):
                # Spread-by-quantity is currently not deterministic from read-only config
                # (controller-side cycle decisions can differ from a static amount model).
                # Keep this channel validated by activity/plan checks in validation layer
                # instead of forcing an exact numeric expectation.
                expected_report_units = None
        elif method in {"prop", "proportional"} and amount is not None:
            ratio_l_per_m3 = amount / 1000
            if (
                expected_water_liters is None
                and flow_lph > 0
                and runtime_minutes is not None
            ):
                expected_water_liters = flow_lph * (runtime_minutes / 60)
            if expected_water_liters is not None:
                expected_water_m3 = expected_water_liters / 1000
                expected_liters = expected_water_m3 * ratio_l_per_m3
                expected_report_units = cls.dosing_report_units_from_liters(
                    expected_liters
                )

            pulse_size_liters = channel.get("dm_pulse_size_liters")
            if (
                ratio_l_per_m3 is not None
                and ratio_l_per_m3 > 0
                and pulse_size_liters is not None
                and flow_lph > 0
            ):
                water_needed_liters = (pulse_size_liters / ratio_l_per_m3) * 1000
                pulse_interval_sec = (water_needed_liters / flow_lph) * 3600
            else:
                pulse_interval_reason = (
                    "Pulse-by-pulse interval unavailable: missing DM pulse size, "
                    "water flow, or proportional ratio"
                )
        elif method in {"calculatedquantity", "calculated_quantity", "calcqty"}:
            if amount is not None:
                expected_report_units = amount
            elif dosing_flow_lph > 0 and runtime_minutes is not None:
                expected_liters = dosing_flow_lph * (runtime_minutes / 60)
                expected_report_units = cls.dosing_report_units_from_liters(
                    expected_liters
                )
        return {
            "channel_id": channel_id,
            "method": channel.get("method"),
            "units": channel.get("units"),
            "amount": amount,
            "flow_lph": dosing_flow_lph,
            "dm_rate": channel.get("dm_rate"),
            "expected_report_units": expected_report_units,
            "ratio_l_per_m3": ratio_l_per_m3,
            "pulse_interval_sec": pulse_interval_sec,
            "pulse_interval_reason": pulse_interval_reason,
            "wm_pulse_size_liters": wm_pulse_size_liters,
            "spread_schedule": spread_schedule,
        }

    @staticmethod
    def _spread_time_schedule(
        configured_amount_minutes: float,
        dosing_window_minutes,
        min_on_delay_sec,
        min_off_delay_sec,
    ):
        time_amount_seconds = max(int(configured_amount_minutes * 60), 0)

        if dosing_window_minutes is None:
            return {
                "valve_number_on_times": 1 if time_amount_seconds > 0 else 0,
                "valve_on_time_seconds": time_amount_seconds,
                "valve_off_time_seconds": 0,
                "delivered_time_seconds": time_amount_seconds,
                "schedule_source": "configured_duration_fallback",
            }

        dosing_window_seconds = max(int(dosing_window_minutes * 60), 0)

        if dosing_window_seconds <= 0:
            return {
                "valve_number_on_times": 0,
                "valve_on_time_seconds": 0,
                "valve_off_time_seconds": 0,
                "delivered_time_seconds": 0,
                "schedule_source": "controller_window",
            }

        min_on_delay_sec = max(int(min_on_delay_sec or 0), 10)
        min_off_delay_sec = max(int(min_off_delay_sec or 0), 10)

        # Firmware parity: calculateAndSetDosingChSpreadByTimeOrCalculatedQuantity()
        if time_amount_seconds >= dosing_window_seconds:
            valve_number_on_times = 1
            valve_on_time = dosing_window_seconds
            valve_off_time = 0
        else:
            total_on_time = time_amount_seconds
            total_off_time = dosing_window_seconds - time_amount_seconds

            valve_number_on_times = total_on_time // min_on_delay_sec
            valve_on_time = 0
            valve_off_time = 0

            if valve_number_on_times > 0:
                valve_off_time = total_off_time // valve_number_on_times
                valve_on_time = min_on_delay_sec

            if valve_off_time < min_off_delay_sec:
                valve_off_time = min_off_delay_sec
                valve_number_on_times = (total_off_time // valve_off_time) + 1
                valve_on_time = total_on_time // valve_number_on_times

        delivered_time_seconds = valve_number_on_times * valve_on_time

        return {
            "valve_number_on_times": valve_number_on_times,
            "valve_on_time_seconds": valve_on_time,
            "valve_off_time_seconds": valve_off_time,
            "delivered_time_seconds": delivered_time_seconds,
            "schedule_source": "controller_window",
        }

    @classmethod
    def find_inconsistencies(cls, config_data: dict, expectations: dict) -> list[str]:
        issues = []
        flow_m3h = config_data.get("flow", 0)
        runtime_minutes = expectations.get("runtime_minutes")
        expected_water_liters = expectations.get("expected_water_liters")

        if (
            flow_m3h > 0
            and runtime_minutes is not None
            and expected_water_liters is not None
        ):
            calculated_water_liters = flow_m3h * 1000 * (runtime_minutes / 60)
            if abs(calculated_water_liters - expected_water_liters) > 0.5:
                issues.append(
                    "POTENTIAL TEST DEFINITION ERROR: runtime/flow water calculation is inconsistent"
                )

        return issues

    @classmethod
    def _report_units_from_liters(cls, liters: float) -> int:
        return round(liters * cls.WATER_REPORT_UNITS_PER_LITER)

    water_report_units_from_liters = _report_units_from_liters
    dosing_report_units_from_liters = _report_units_from_liters
