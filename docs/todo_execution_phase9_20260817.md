# Execution TODOs Phase 9 - 2026-08-17

Phase 9 adds named analyzer profiles to reduce repetitive CLI setup.

## TODO List

- [x] 1. Re-read current main and validation state after user edits.
- [x] 2. Add named analyzer profiles in main.
- [x] 3. Add profile for Program 7 strict with safe fallback.
- [x] 4. Add profile for Program 7 strict + Program 8 lab.
- [x] 5. Keep profile off by default.
- [x] 6. Ensure explicit CLI flags override profile-populated values.
- [x] 7. Add smoke test for profile expansion behavior.
- [x] 8. Run diagnostics on updated files.
- [x] 9. Run smoke test and argparse help.
- [x] 10. Document direct CLI examples.

## Validation

- main.py diagnostics -> no errors
- scripts/smoke_analyzer_profiles.py -> PASS
- main.py --help -> PASS

## Direct CLI Usage

- Program 7 strict, all others safe:
  - python main.py --analyzer-profile spread7-strict

- Program 7 strict, Program 8 lab, all others safe:
  - python main.py --analyzer-profile spread7-strict-calc8-lab

- Profile plus explicit override:
  - python main.py --analyzer-profile spread7-strict --analyzer-policy-map "7:lab,\*:strict"
