def assert_monitoring_clean(summary: dict, anomaly_blocklist: set[str]):

    blocked = []

    for anomaly in summary["anomalies"]:
        _, _, anomaly_type, line = anomaly

        if anomaly_type in anomaly_blocklist:
            blocked.append((anomaly_type, line))

    if not blocked:
        return

    details = "\n".join(
        f"- {anomaly_type}: {line}"
        for anomaly_type, line in blocked[:10]
    )

    raise AssertionError("Blocked monitoring anomalies detected:\n" f"{details}")
