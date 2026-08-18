# Execution TODOs Phase 12 - 2026-08-17

Phase 12 adds a dry-run mode to print the effective runtime/analyzer configuration without touching hardware.

## TODO List

- [x] 1. Re-read current runner state.
- [x] 2. Add dry-run-config CLI flag.
- [x] 3. Print effective analyzer/runtime settings.
- [x] 4. Include resolved auto profile in output.
- [x] 5. Include active scenarios in output.
- [x] 6. Exit before WM sync or controller connect.
- [x] 7. Validate analyzer policy settings in dry-run mode.
- [x] 8. Add smoke test for dry-run output.
- [x] 9. Run diagnostics and smoke test.
- [x] 10. Document direct usage.

## Notes

- Dry-run is safe: no serial connection, no sync command, no hook execution.

## Validation

- main.py diagnostics -> no errors
- scripts/smoke_dry_run_config.py -> PASS

## Direct Usage

- Show effective configuration with auto profile resolution:
  - python main.py --analyzer-profile auto --dry-run-config

- Show effective configuration for a strict preset:
  - python main.py --analyzer-profile spread7-strict --dry-run-config

- Show effective configuration with explicit map override:
  - python main.py --analyzer-profile spread7-strict --analyzer-policy-map "7:lab,\*:strict" --dry-run-config
