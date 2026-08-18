# Execution TODOs Phase 10 - 2026-08-17

Phase 10 moves analyzer profile definitions to external config with built-in fallback defaults.

## TODO List

- [x] 1. Re-read current main and auto-profile smoke flow.
- [x] 2. Add external analyzer profiles JSON config.
- [x] 3. Keep built-in fallback defaults when file is missing.
- [x] 4. Add CLI flag for analyzer profiles file path.
- [x] 5. Load profiles before argparse choices are built.
- [x] 6. Keep auto-profile logic working with loaded profiles.
- [x] 7. Update auto-profile smoke to use loaded profiles.
- [x] 8. Add fallback smoke for missing profiles file.
- [x] 9. Run diagnostics and smoke tests.
- [x] 10. Document direct usage expectations.

## Validation

- main.py diagnostics -> no errors
- scripts/smoke_auto_analyzer_profile.py -> PASS
- scripts/smoke_analyzer_profiles_file_fallback.py -> PASS
- main.py --help -> PASS

## Usage Notes

- Default profiles file:
  - config/analyzer_profiles.json
- Custom profiles file:
  - python main.py --analyzer-profiles-file path/to/profiles.json
- If the file is missing, built-in fallback profiles are used automatically.
