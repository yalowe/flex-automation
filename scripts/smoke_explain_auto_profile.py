#!/usr/bin/env python
"""
Smoke test for --explain-auto-profile inspection command.

Verifies that:
- --explain-auto-profile resolves to the currently active profile
- When Program 7 is active, it resolves to 'spread7-strict'
- Output shows profile details (policy, policy_map, default_policy)
- Command exits cleanly after explanation
"""

import subprocess
import sys


def run_explain_auto_profile():
    """Run main.py with --explain-auto-profile and capture output."""
    cmd = [
        sys.executable,
        "main.py",
        "--explain-auto-profile",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")
    return result


def main():
    print("=" * 70)
    print("SMOKE TEST: --explain-auto-profile inspection command")
    print("=" * 70)

    result = run_explain_auto_profile()

    print(f"Exit Code: {result.returncode}")
    print("\nStdout:")
    print(result.stdout)

    if result.stderr:
        print("\nStderr:")
        print(result.stderr)

    # Validation
    checks = [
        ("Exit code 0", result.returncode == 0),
        ("Output contains 'ANALYZER PROFILE'", "ANALYZER PROFILE" in result.stdout),
        ("Output shows Requested Name", "Requested Name" in result.stdout),
        ("Output shows Resolved Name", "Resolved Name" in result.stdout),
        ("Output shows Policy field", "Policy" in result.stdout),
        ("Output shows Policy Map field", "Policy Map" in result.stdout),
        ("Output shows Default Policy field", "Default Policy" in result.stdout),
        ("Resolved name is 'auto'", "Requested Name   : auto" in result.stdout),
        (
            "Resolves to spread7-strict (Program 7 active)",
            "Resolved Name    : spread7-strict" in result.stdout,
        ),
        (
            "Shows 'safe' policy (spread7-strict policy)",
            "Policy           : safe" in result.stdout,
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
