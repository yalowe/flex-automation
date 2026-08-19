import argparse
import json
import os
import sys
import time

import serial


def load_settings(settings_path):
    with open(settings_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    wm_cycles = {}
    for wm_id in range(1, 6):
        entry = raw.get(str(wm_id), {})
        cycle_ms = str(entry.get("cycle_ms", "1000")).strip()
        try:
            cycle_value = float(cycle_ms)
        except ValueError as exc:
            raise ValueError(f"Invalid cycle_ms for WM{wm_id}: {cycle_ms}") from exc

        if cycle_value <= 0:
            raise ValueError(f"Invalid cycle_ms for WM{wm_id}: {cycle_ms}")
        wm_cycles[wm_id] = cycle_ms

    return wm_cycles


def send_line(ser, cmd):
    ser.write((cmd + "\n").encode("utf-8"))
    time.sleep(0.12)


def main():
    parser = argparse.ArgumentParser(
        description="Apply saved wm_settings.json trigger rates to board without opening GUI."
    )
    parser.add_argument("--port", required=True, help="Serial port (example: COM7)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument(
        "--settings",
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "wm_settings.json"),
        help="Path to wm_settings.json",
    )
    args = parser.parse_args()

    try:
        cycles = load_settings(args.settings)
    except Exception as exc:
        print(f"Failed to load settings: {exc}")
        return 1

    try:
        with serial.Serial(args.port, args.baud, timeout=1, dsrdtr=False, rtscts=False) as ser:
            ser.dtr = False
            ser.rts = False
            time.sleep(0.3)

            for wm_id in range(1, 6):
                cmd = f"trigger wm {wm_id} {cycles[wm_id]}"
                send_line(ser, cmd)
                print(f"Sent: {cmd}")

            send_line(ser, "get status")
            print("Sent: get status")
    except Exception as exc:
        print(f"Serial error: {exc}")
        return 2

    print("Done. Board now stores these WM trigger cycles in flash.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
