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

    pattern = r"Program Id:\s*\d+.*?State:\s*(\w+)"

    print(pattern)
    print(report_text)

    match = re.search(pattern, report_text)

    print(match.group(0) if match else None)

    if not match:
        print(None)
        return False

    extracted_state = match.group(1).strip()
    print(extracted_state)

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

def estimate_timeout_sec(fallback_wait_sec: int, program_units, shift_amount: int) -> int:

    default_timeout = max(fallback_wait_sec + 300, 600)

    if not program_units:
        return default_timeout

    normalized_units = program_units.strip().lower()

    if normalized_units == "time" and shift_amount > 0:
        return max((shift_amount * 60) + 300, default_timeout)

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
