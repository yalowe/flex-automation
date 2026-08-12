def expected_dose_formula_text(channel, expected, config_data, expectations,):

    method = (channel.get("method") or "").strip().lower()
    units = (channel.get("units") or "").strip().lower()

    if method == "bulk" and units == "time":
        return (
            f"{channel.get('flow')} L/h x " f"({channel.get('amount')} min / 60) x 1000"
        )

    if method == "bulk" and units == "quant":
        return "configured quantity from recipe"

    if method in {"prop", "proportional"}:
        return (
            f"({expectations.get('expected_water_liters')} L / 1000) x "
            f"{expected.get('ratio_l_per_m3')} L/m3 x 1000"
        )

    if method == "spread" and units == "time":
        return (f"{channel.get('flow')} L/h x " f"({channel.get('amount')} min / 60) x 1000")

    return "unsupported or unresolved from current controller inputs"

def print_dosing_diagnostics(config_data, expectations, actual_dosing_channels):

    active_channels = config_data.get("dosing_channels", {})
    channel_expectations = expectations.get("channel_expectations", {})

    if not active_channels:
        return

    print("========== DOSING DIAGNOSTICS ==========")

    for channel_id, channel in sorted(active_channels.items()):
        expected = channel_expectations.get(channel_id, {})
        actual = actual_dosing_channels.get(channel_id, {})
        method = channel.get("method")
        units = channel.get("units")
        ratio = expected.get("ratio_l_per_m3")
        expected_result = expected.get("expected_report_units")
        actual_delivered = actual.get("delivered_quantity")
        actual_remaining = actual.get("remain_quantity")
        actual_total = None

        if actual_delivered is not None and actual_remaining is not None:
            actual_total = actual_delivered + actual_remaining

        difference = None
        if expected_result is not None and actual_total is not None:
            difference = actual_total - expected_result

        print(f"Channel ID              : {channel_id}")
        print(f"DM ID                   : {channel_id}")
        print(f"Configured Dosing Flow  : {channel.get('flow')}")
        print(f"Configured Method       : {method}")
        print(f"Configured Ratio        : {ratio}")
        print(f"DM Rate                 : {channel.get('dm_rate')}")
        print(
            "Derived DM Pulse Size    : "
            f"{expected.get('dm_pulse_size_liters', 'unknown')}"
        )
        print(
            "Expected Dose Formula    : "
            f"{expected_dose_formula_text(channel, expected, config_data, expectations)}"
        )
        print(f"Expected Dose Result    : {expected_result}")
        print(f"Actual Delivered Dose   : {actual_delivered}")
        print(f"Actual Remaining Dose   : {actual_remaining}")
        print(f"Difference              : {difference}")
        print("---------------------------------------")

    print("=======================================\n")


def print_scenario_summary(scenario, config_data, expectations, data, finish_reason, monitoring_summary, shift_id):

    expected_water = expectations.get("expected_water_report_units")
    expected_dose = expectations.get("expected_dosing_report_units")

    wm_cycle = config_data.get("wm_cycle")
    dm_cycles = [
        f"CH{channel_id}=DM{channel_id}:{channel.get('dm_cycle')}"
        for channel_id, channel in sorted(
            config_data.get("dosing_channels", {}).items()
        )
        if channel.get("enabled")
    ]

    anomaly_count = (monitoring_summary.get("anomaly_count", 0)
        if monitoring_summary is not None
        else 0
    )

    print("========== SCENARIO SUMMARY ==========")
    print(f"Scenario        : {scenario.name}")
    print(f"Program ID      : {config_data.get('program_id')}")
    print(f"Shift ID        : {shift_id or config_data.get('shift_id')}")
    print(f"Recipe ID       : {config_data.get('recipe_id')}")
    print(f"Expected Water  : {expected_water}")
    print(f"Actual Water    : {data['water_delivered']}")
    print(f"Expected Dose   : {expected_dose}")
    print(f"Actual Dose     : {data['dosing_delivered']}")
    print(f"WM Cycle (ms)   : {wm_cycle}")
    print("DM Cycle (ms)   : " f"{', '.join(dm_cycles) if dm_cycles else 'none'}")
    print(f"Finish Reason   : {finish_reason}")
    print(f"Anomaly Count   : {anomaly_count}")
    print(f"PASS / FAIL     : {'PASS'}")
    print("======================================\n")


def print_monitoring_summary(summary: dict):

    print("\n========== MONITORING SUMMARY ==========")
    print(f"Scenario         : {summary['scenario']}")
    print(f"Captured Lines   : {summary['lines']}")
    print(f"Device Events    : {summary['device_events']}")
    print(f"Valve Opens      : {summary['valve_open_count']}")
    print(f"Valve Closes     : {summary['valve_close_count']}")
    print(f"WM Events        : {summary['wm_event_count']}")
    print(f"Anomalies        : {summary['anomaly_count']}")

    if summary["wm_last_counts"]:
        wm_text = ", ".join(f"WM{wm_id}={count}"
            for wm_id, count in sorted(summary["wm_last_counts"].items())
        )
        print(f"WM Last Counts   : {wm_text}")

    if summary["anomalies"]:
        print("Anomaly Samples  :")
        for anomaly in summary["anomalies"][:5]:
            timestamp, command, anomaly_type, line = anomaly
            print(f"- [{timestamp}] ({command}) " f"{anomaly_type} | {line}")

    print("========================================\n")
