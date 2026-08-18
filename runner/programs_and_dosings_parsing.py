import math
import re


def start_times_match(
    expected_start_time: str,
    report_start_time: str,
) -> bool:

    if expected_start_time == report_start_time:
        return True

    expected_parts = expected_start_time.split(":")
    report_parts = report_start_time.split(":")

    if len(expected_parts) >= 2 and len(report_parts) >= 2:
        expected_hm = ":".join(expected_parts[:2])
        report_hm = ":".join(report_parts[:2])
        if expected_hm == report_hm:
            return True

    return False


def report_state_is_running(report_text: str) -> bool:

    pattern = r"Program Id:\s*(\d+).*?State:\s*(\w+)"
    match = re.search(pattern, report_text)

    if not match:
        return False

    program_id = match.group(1).strip()
    extracted_state = match.group(2).strip()

    print(f"Program ID: {program_id}, State: {extracted_state}")
    return extracted_state.lower() == "running"

def extract_program_units(programs_info: str, program_id: int):

    for line in programs_info.splitlines():
        row_match = re.match(r"\s*(\d+)\|", line)

        if not row_match:
            continue

        if int(row_match.group(1)) != program_id:
            continue

        parts = [part.strip() for part in line.split("|")]

        if len(parts) > 5:
            return parts[5]
        
    return None

def estimate_timeout_sec(
    config_data: dict | None = None,
    fallback_wait_sec: int | None = None,
    program_units=None,
    shift_amount: int = 0,
    water_before: int = 0,
    water_after: int = 0,
    flow: float = 0.0,
) -> int:

    if config_data is not None:
        program_units = config_data.get("program_units", program_units)
        shift_amount = config_data.get("shift_amount", shift_amount)
        water_before = config_data.get("water_before", water_before)
        water_after = config_data.get("water_after", water_after)
        flow = config_data.get("flow", flow)

    fallback_wait_sec = fallback_wait_sec if fallback_wait_sec is not None else 600
    default_timeout = max(fallback_wait_sec + 300, 600)

    if not program_units:
        return default_timeout

    normalized_units = str(program_units).strip().lower()

    if normalized_units == "time" and shift_amount > 0:
        runtime_sec = (shift_amount * 60) + ((water_before + water_after) * 60)
        return max(runtime_sec + 300, default_timeout)

    if shift_amount <= 0:
        return default_timeout

    effective_flow_lph = max(float(flow) * 1000.0, 0.0)
    if effective_flow_lph <= 0:
        return default_timeout

    planned_liters = shift_amount / 100.0
    runtime_sec = (planned_liters / effective_flow_lph) * 3600.0
    runtime_sec += (water_before + water_after) * 60

    if normalized_units in {"quantity", "qty", "quant", "depth", "mm", "millimeter", "millimeters"}:
        return max(int(math.ceil(runtime_sec + 300)), default_timeout)

    return default_timeout


def extract_active_program_state(programs_info: str):

    active_program_id = None
    active_program_state = None

    for line in programs_info.splitlines():
        if "ProgramID:" in line:
            match = re.search(r"ProgramID:\s*(\d+)", line)
            if match:
                active_program_id = int(match.group(1))

        if "Program State:" in line:
            match = re.search(r"Program State:\s*(\w+)", line)
            if match:
                active_program_state = match.group(1)

    return active_program_id, active_program_state


def extract_report_shift_id(report_text: str):

    match = re.search(r"Shift Id:\s*(\d+)", report_text)

    if not match:
        return None

    return int(match.group(1))


def configured_expected_dose(config_data: dict):

    dosing_channels = config_data.get("dosing_channels", {})

    amounts = [
        channel.get("amount")
        for channel in dosing_channels.values()
        if channel.get("enabled") and channel.get("amount") is not None
    ]

    if not amounts:
        return None

    return sum(amounts)
