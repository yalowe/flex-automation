# Execution TODOs Phase 3 - 2026-08-17

Phase 3 focuses on safe headless analyzer integration with zero impact by default.

## TODO List

- [x] 1. Re-read changed runtime files before new edits.
- [x] 2. Add optional post-scenario headless analyzer hook (disabled by default).
- [x] 3. Keep hook command configurable using environment variable.
- [x] 4. Add strict/non-strict hook failure policy.
- [x] 5. Keep existing scenario failure/anomaly behavior unchanged when hook disabled.
- [x] 6. Surface hook stdout/stderr to console for debugging.
- [x] 7. Add smoke script for headless hook path without hardware dependency.
- [x] 8. Run diagnostics on modified files.
- [x] 9. Run smoke script and verify PASS.
- [x] 10. Document hook usage examples.

## Notes

- Hook entrypoint: tests.programs_and_dosings._run_headless_analyzer_hook
- Env vars:
  - FLEX_HEADLESS_ANALYZER_CMD
  - FLEX_HEADLESS_ANALYZER_STRICT
- Validation results:
  - tests/programs_and_dosings.py diagnostics -> no errors
  - scripts/smoke_headless_hook.py -> PASS

## Safe Usage Examples

- Hook disabled (default):
  - python main.py

- Hook enabled (non-strict):
  - set FLEX_HEADLESS_ANALYZER_CMD=python -c "print('post-check for {scenario_name} {program_id}')"
  - python main.py

- Hook enabled (strict fail on analyzer error):
  - set FLEX_HEADLESS_ANALYZER_CMD=python -c "import sys; sys.exit(2)"
  - set FLEX_HEADLESS_ANALYZER_STRICT=true
  - python main.py
