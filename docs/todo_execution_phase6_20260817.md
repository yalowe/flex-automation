# Execution TODOs Phase 6 - 2026-08-17

Phase 6 wires analyzer policy presets directly into main CLI to avoid manual environment setup.

## TODO List

- [x] 1. Re-read current main and policy scripts after user edits.
- [x] 2. Add analyzer policy CLI flag to main (off/safe/strict/lab).
- [x] 3. Add analyzer policy script path override flag.
- [x] 4. Auto-generate FLEX_HEADLESS_ANALYZER_CMD from selected policy.
- [x] 5. Auto-set FLEX_HEADLESS_ANALYZER_STRICT for strict policy by default.
- [x] 6. Keep policy off by default for backward compatibility.
- [x] 7. Add smoke script for wiring logic without hardware.
- [x] 8. Run diagnostics on modified files.
- [x] 9. Run smoke for policy wiring and argparse help.
- [x] 10. Document direct CLI usage examples.

## Validation

- main.py diagnostics -> no errors
- scripts/smoke_main_analyzer_policy_wiring.py -> PASS
- main.py --help -> PASS

## Direct CLI Usage

- No analyzer hook (default behavior):
  - python main.py

- Safe policy via CLI:
  - python main.py --analyzer-policy safe

- Strict policy via CLI:
  - python main.py --analyzer-policy strict

- Custom policy wrapper path:
  - python main.py --analyzer-policy safe --analyzer-policy-script scripts/headless_monitor_policy.py
