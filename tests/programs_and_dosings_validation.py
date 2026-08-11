from services.expectation_builder import ExpectationBuilder


def verify_tolerance(
    actual,
    expected,
    tolerance_percent,
):

    delta = expected * tolerance_percent / 100

    return abs(actual - expected) <= delta


def validate_results_from_controller(
    config_data,
    expectations,
    data,
    scenario=None,
):

    documented_issues = []

    if scenario is not None:
        documented_issues = (
            ExpectationBuilder.compare_documented_expectations(
                expectations=expectations,
                documented_water=scenario.expected_water,
                documented_dosing=scenario.expected_dosing,
            )
        )

    for issue in expectations.get("inconsistencies", []):
        print(issue)

    for issue in documented_issues:
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
        "Controller-driven validation failed: "
        "water_time must be non-negative"
    )

    active_dosing_channels = config_data.get("dosing_channels", {})
    enabled_channels = [
        channel
        for channel in active_dosing_channels.values()
        if channel.get("enabled")
    ]

    if expected_plan is not None:
        actual_plan = (
            data["dosing_delivered"]
            + data["dosing_remaining"]
        )

        assert verify_tolerance(
            actual=actual_plan,
            expected=expected_plan,
            tolerance_percent=15,
        ), (
            "Controller-driven validation failed: "
            f"dosing_plan={actual_plan} "
            f"expected={expected_plan}"
        )
    elif enabled_channels:
        total_dosing = (
            data["dosing_delivered"]
            + data["dosing_remaining"]
        )

        assert total_dosing > 0, (
            "Controller-driven validation failed: "
            "enabled dosing channels require dosing activity"
        )

    assert data["dosing_remaining"] >= 0, (
        "Controller-driven validation failed: "
        "dosing_remaining must be non-negative"
    )
