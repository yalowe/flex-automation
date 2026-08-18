# Execution TODOs Phase 8 - 2026-08-17

Phase 8 validates analyzer policy-map syntax and fails fast with friendly messages.

## TODO List

- [x] 1. Re-read current main and hook files after user edits.
- [x] 2. Create shared analyzer policy parsing module.
- [x] 3. Add explicit runtime-policy validation.
- [x] 4. Validate analyzer default policy.
- [x] 5. Validate analyzer policy-map item format.
- [x] 6. Validate analyzer policy-map keys (program id or '\*').
- [x] 7. Reuse same parser in main and scenario hook.
- [x] 8. Add smoke test for malformed mapping with friendly error.
- [x] 9. Re-run valid mapping smoke test after refactor.
- [x] 10. Confirm diagnostics are clean.

## Validation

- services/analyzer_policy.py diagnostics -> no errors
- main.py diagnostics -> no errors
- tests/programs_and_dosings.py diagnostics -> no errors
- scripts/smoke_policy_map_resolution.py -> PASS
- scripts/smoke_invalid_policy_map.py -> PASS

## Behavior

- Valid mapping example:
  - 7:strict,8:lab,\*:safe
- Invalid mapping example:
  - 7-strict,\*:safe
- Invalid configuration now fails fast with a clear message before runtime starts.
