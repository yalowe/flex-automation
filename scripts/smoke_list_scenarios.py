#!/usr/bin/env python
"""
Smoke test for --list-scenarios inspection command.

Verifies that:
- --list-scenarios displays all active scenarios with program IDs
- Command exits cleanly after listing
- Output is properly formatted
"""

import subprocess
import sys


def run_list_scenarios():
    """Run main.py with --list-scenarios and capture output."""
    cmd = [
        sys.executable,
        "main.py",
        "--list-scenarios",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")
    return result


def main():
    print("=" * 70)
    print("SMOKE TEST: --list-scenarios inspection command")
    print("=" * 70)

    result = run_list_scenarios()

    print(f"Exit Code: {result.returncode}")
    print("\nStdout:")
    print(result.stdout)

    if result.stderr:
        print("\nStderr:")
        print(result.stderr)

    # Validation
    checks = [
        ("Exit code 0", result.returncode == 0),
        ("Output contains 'ACTIVE SCENARIOS'", "ACTIVE SCENARIOS" in result.stdout),
        ("Output contains 'Program ID'", "Program ID" in result.stdout),
        (
            "Output contains scenario names",
            any(program in result.stdout for program in ["Spread By Quantity"]),
        ),
    ]

    print("\n" + "=" * 70)
    print("VALIDATION RESULTS:")
    print("=" * 70)
    all_pass = True
    for check_name, passed in checks:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status}: {check_name}")
        if not passed:
            all_pass = False

    print("=" * 70)
    if all_pass:
        print("OVERALL: [PASS]")
        sys.exit(0)
    else:
        print("OVERALL: [FAIL]")
        sys.exit(1)


if __name__ == "__main__":
    main()
