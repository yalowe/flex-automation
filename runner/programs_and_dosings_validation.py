"""Validation layer for controller-driven irrigation expectations.

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
- services/irrigation_service.py::IrrigationService.run_program and related execution methods
  controller command: "IrrCmd Set ..."
  supported configuration: irrigation execution state only; no controller configuration
  writes are implemented in this project yet
"""


def verify_tolerance(
    actual,
    expected,
    tolerance_percent,
):

    delta = expected * tolerance_percent / 100

    return abs(actual - expected) <= delta


def _is_quantity_unit(unit_value) -> bool:
    return (unit_value or "").strip().lower() in {
        "quant",
        "qty",
        "quantity",
        "depth",
    }


def _is_spread_quantity_channel(channel: dict, program_units: str) -> bool:
    method = (channel.get("method") or "").strip().lower()
    units = (channel.get("units") or "").strip().lower()

    if method != "spread":
        return False

    return _is_quantity_unit(units) or _is_quantity_unit(program_units)


def _validate_program7_spread_quantity_channels(
    *,
    config_data: dict,
    actual_dosing_channels: dict,
) -> None:
    """Program 7 guardrail: verify spread/quantity channels exist in report and carry usable values."""

    program_units = (config_data.get("program_units") or "").strip().lower()
    active_channels = config_data.get("dosing_channels", {})

    target_channel_ids = [
        channel_id
        for channel_id, channel in sorted(active_channels.items())
        if channel.get("enabled")
        and _is_spread_quantity_channel(channel, program_units)
    ]

    if not target_channel_ids:
        return

    for channel_id in target_channel_ids:
        actual_channel = actual_dosing_channels.get(channel_id)
        assert actual_channel is not None, (
            "Controller-driven validation failed: "
            f"missing dosing channel {channel_id} in completed report"
        )

        plan_amount = actual_channel.get("plan_amount")
        delivered_quantity = actual_channel.get("delivered_quantity")
        remain_quantity = actual_channel.get("remain_quantity")

        assert plan_amount is not None and plan_amount > 0, (
            "Controller-driven validation failed: "
            f"channel {channel_id} spread/quantity plan_amount must be > 0"
        )

        assert delivered_quantity is not None and remain_quantity is not None, (
            "Controller-driven validation failed: "
            f"channel {channel_id} missing delivered/remain values"
        )

        assert (delivered_quantity + remain_quantity) > 0, (
            "Controller-driven validation failed: "
            f"channel {channel_id} spread/quantity has no dosing activity"
        )


def validate_results_from_controller(
    config_data,
    expectations,
    data,
    scenario=None,
    actual_dosing_channels=None,
):

    for issue in expectations.get("inconsistencies", []):
        print(issue)

        print(issue)

    flow = config_data.get("flow", 0)

    expected_water = expectations.get("expected_water_report_units")
    expected_dosing = expectations.get("expected_dosing_report_units")
    expected_plan = expectations.get("expected_plan_report_units")

    if expected_water is not None:
        assert verify_tolerance(
            actual=data["water_delivered"],
            expected=expected_water,
            tolerance_percent=10,
        ), (
            "Controller-driven validation failed: "
            f"water_delivered={data['water_delivered']} "
            f"expected={expected_water}"
        )
    elif flow > 0:
        assert data["water_delivered"] > 0, (
            "Controller-driven validation failed: "
            "water_delivered must be > 0 when flow > 0"
        )

    assert data["water_time"] >= 0, (
        "Controller-driven validation failed: " "water_time must be non-negative"
    )

    active_dosing_channels = config_data.get("dosing_channels", {})
    enabled_channels = [
        channel for channel in active_dosing_channels.values() if channel.get("enabled")
    ]

    if expected_plan is not None:
        actual_plan = data["dosing_delivered"] + data["dosing_remaining"]

        assert verify_tolerance(
            actual=actual_plan,
            expected=expected_plan,
            tolerance_percent=15,
        ), (
            "Controller-driven validation failed: "
            f"dosing_plan={actual_plan} "
            f"expected={expected_plan}"
        )
    elif expected_dosing is not None:
        actual_plan = data["dosing_delivered"] + data["dosing_remaining"]

        assert verify_tolerance(
            actual=actual_plan,
            expected=expected_dosing,
            tolerance_percent=15,
        ), (
            "Controller-driven validation failed: "
            f"dosing_plan={actual_plan} "
            f"expected={expected_dosing}"
        )

    elif enabled_channels:
        total_dosing = data["dosing_delivered"] + data["dosing_remaining"]

        assert total_dosing > 0, (
            "Controller-driven validation failed: "
            "enabled dosing channels require dosing activity"
        )

    assert data["dosing_remaining"] >= 0, (
        "Controller-driven validation failed: " "dosing_remaining must be non-negative"
    )

    if (
        scenario is not None
        and getattr(scenario, "program_id", None) == 7
        and actual_dosing_channels is not None
    ):
        _validate_program7_spread_quantity_channels(
            config_data=config_data,
            actual_dosing_channels=actual_dosing_channels,
        )
