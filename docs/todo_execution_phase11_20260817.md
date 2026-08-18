# Execution TODOs Phase 11 - 2026-08-17

Phase 11 validates the external analyzer profiles file structure and fails early with clear messages.

## TODO List

- [x] 1. Re-read current profile-loading implementation.
- [x] 2. Validate profile policy field against allowed values.
- [x] 3. Validate default_policy for runtime-enabled profiles.
- [x] 4. Validate policy_map syntax for runtime-enabled profiles.
- [x] 5. Reject policy_map when policy is off.
- [x] 6. Keep missing-file fallback behavior unchanged.
- [x] 7. Add smoke test for malformed profiles file.
- [x] 8. Re-run fallback smoke after validation change.
- [x] 9. Run diagnostics on touched files.
- [x] 10. Document the new failure mode.

## Validation

- main.py diagnostics -> no errors
- config/analyzer_profiles.json diagnostics -> no errors
- scripts/smoke_invalid_analyzer_profiles_file.py -> PASS
- scripts/smoke_analyzer_profiles_file_fallback.py -> PASS

## Failure Behavior

- Invalid profiles file now fails early during startup/profile loading.
- Example invalid profile:
  - policy=safe with policy_map=7-strict,\*:safe
- Example invalid profile:
  - policy=off with non-empty policy_map
