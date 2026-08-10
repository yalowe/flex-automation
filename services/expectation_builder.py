class ExpectationBuilder:
    """Build expected controller behavior from runtime-discovered config."""

    WATER_REPORT_UNITS_PER_LITER = 100
    DOSING_REPORT_UNITS_PER_LITER = 100

    @classmethod
    def build(cls, config_data: dict) -> dict:
        flow_m3h = config_data.get("flow", 0)
        flow_lph = flow_m3h * 1000
        shift_amount = config_data.get("shift_amount", 0)
        program_units = (config_data.get("program_units") or "").strip().lower()
        water_before = config_data.get("water_before", 0)
        water_after = config_data.get("water_after", 0)

        runtime_minutes = None
        expected_water_report_units = None
        expected_water_liters = None

        if program_units == "time" and shift_amount > 0:
            runtime_minutes = shift_amount
            expected_water_liters = flow_lph * (runtime_minutes / 60)
            expected_water_report_units = cls.water_report_units_from_liters(
                expected_water_liters
            )
        elif program_units == "quant" and shift_amount > 0:
            expected_water_report_units = shift_amount

        dosing_window_minutes = None
        if runtime_minutes is not None:
            dosing_window_minutes = max(
                runtime_minutes - water_before - water_after,
                0,
            )

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
                expected_water_liters=expected_water_liters,
                flow_lph=flow_lph,
                wm_pulse_size_liters=config_data.get("water_meter_pulse_liters"),
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
                expected_plan_report_units
                if has_supported_dosing_expectation
                else None
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
        expected_water_liters,
        flow_lph,
        wm_pulse_size_liters,
    ) -> dict:
        method = (channel.get("method") or "").strip().lower()
        units = (channel.get("units") or "").strip().lower()
        amount = channel.get("amount")
        dosing_flow_lph = channel.get("flow", 0)

        expected_report_units = None
        ratio_l_per_m3 = None
        pulse_interval_sec = None
        pulse_interval_reason = None

        if method == "bulk" and units == "time" and amount is not None:
            expected_liters = dosing_flow_lph * (amount / 60)
            expected_report_units = cls.dosing_report_units_from_liters(
                expected_liters
            )
        elif method == "bulk" and units == "quant" and amount is not None:
            expected_report_units = amount
        elif method in {"prop", "proportional"} and amount is not None:
            ratio_l_per_m3 = amount / 1000
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
        elif method == "spread" and units == "time" and amount is not None:
            if dosing_window_minutes is not None:
                expected_liters = dosing_flow_lph * (amount / 60)
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
        }

    @classmethod
    def find_inconsistencies(cls, config_data: dict, expectations: dict) -> list[str]:
        issues = []
        flow_m3h = config_data.get("flow", 0)
        runtime_minutes = expectations.get("runtime_minutes")
        expected_water_liters = expectations.get("expected_water_liters")

        if flow_m3h > 0 and runtime_minutes is not None and expected_water_liters is not None:
            calculated_water_liters = flow_m3h * 1000 * (runtime_minutes / 60)
            if abs(calculated_water_liters - expected_water_liters) > 0.5:
                issues.append(
                    "POTENTIAL TEST DEFINITION ERROR: runtime/flow water calculation is inconsistent"
                )

        return issues

    @classmethod
    def compare_documented_expectations(
        cls,
        expectations: dict,
        documented_water,
        documented_dosing,
        threshold_percent=20,
    ) -> list[str]:
        issues = []

        built_water = expectations.get("expected_water_report_units")
        built_dosing = expectations.get("expected_dosing_report_units")

        if cls._is_large_mismatch(built_water, documented_water, threshold_percent):
            issues.append(
                "POTENTIAL TEST DEFINITION ERROR: documented water expectation differs from controller-driven expectation"
            )

        if cls._is_large_mismatch(built_dosing, documented_dosing, threshold_percent):
            issues.append(
                "POTENTIAL TEST DEFINITION ERROR: documented dosing expectation differs from controller-driven expectation"
            )

        return issues

    @staticmethod
    def _is_large_mismatch(expected, documented, threshold_percent):
        if expected is None or documented in (None, 0):
            return False

        delta = expected * threshold_percent / 100
        return abs(expected - documented) > delta

    @classmethod
    def water_report_units_from_liters(cls, liters: float) -> int:
        return round(liters * cls.WATER_REPORT_UNITS_PER_LITER)

    @classmethod
    def dosing_report_units_from_liters(cls, liters: float) -> int:
        return round(liters * cls.DOSING_REPORT_UNITS_PER_LITER)
