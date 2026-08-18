import time

from runner.programs_and_dosings_parsing import extract_active_program_state


def wait_until_program_not_running(
    irrigation,
    timeout_sec=120,
    poll_sec=2,
    raise_on_timeout=True,
):

    timeout = time.time() + timeout_sec

    while time.time() < timeout:
        programs_info = irrigation.programs_info().response
        _, active_program_state = extract_active_program_state(
            programs_info
        )

        if active_program_state != "Running":
            print(
                "Controller is no longer in Running state. "
                "Starting target program..."
            )
            return True

        time.sleep(poll_sec)

    if raise_on_timeout:
        raise TimeoutError( "Timeout waiting for controller to leave Running state")

    return False

def skip_all_running_shifts(irrigation, fallback_program_id, max_shift_skips=20, poll_sec=2):

    for skip_index in range(max_shift_skips):
        programs_info = irrigation.programs_info().response
        active_program_id, active_program_state = (
            extract_active_program_state(programs_info))

        if active_program_state != "Running":
            print(
                "Controller is no longer in Running state. "
                "Starting target program..."
            )
            return

        running_program_id = (active_program_id if active_program_id is not None else fallback_program_id)

        print(
            f"Skipping shift #{skip_index + 1} "
            f"for Program {running_program_id}..."
        )

        skip_shift_result = irrigation.skip_shift(running_program_id)

        assert skip_shift_result.success, (
            "Failed to skip running shift before restart. "
            f"Response: {skip_shift_result.response}"
        )

        if wait_until_program_not_running(irrigation=irrigation, timeout_sec=10, poll_sec=poll_sec, raise_on_timeout=False):
            return

    raise TimeoutError("Timeout while skipping all running shifts before restart")


def stop_running_program(irrigation, active_program_id, target_program_id):

    running_program_id = (active_program_id if active_program_id is not None else target_program_id)

    print("Detected running program. "
        f"Skipping Program {running_program_id} before restart..."
    )

    skip_program_result = irrigation.skip_program(running_program_id)

    assert skip_program_result.success, (
        "Failed to skip running program before restart. "
        f"Response: {skip_program_result.response}"
    )

    if wait_until_program_not_running(irrigation=irrigation, timeout_sec=20, poll_sec=2, raise_on_timeout=False):
        return

    print(
        "Program is still running after skip program command. "
        "Skipping remaining shifts..."
    )

    skip_all_running_shifts(irrigation=irrigation, fallback_program_id=running_program_id, max_shift_skips=20, poll_sec=2,)
