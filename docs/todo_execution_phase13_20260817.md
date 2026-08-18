# Execution TODOs Phase 13 - 2026-08-17

Phase 13 adds safe CLI inspection commands for loaded analyzer profiles.

## TODO List

- [x] 1. Re-read current main/profile loading flow.
- [x] 2. Add list-analyzer-profiles CLI flag.
- [x] 3. Add explain-analyzer-profile CLI option.
- [x] 4. Resolve auto profile for explain mode.
- [x] 5. Exit before hardware actions for list/explain commands.
- [x] 6. Keep dry-run and runtime behavior unchanged.
- [x] 7. Add smoke test for list and explain flows.
- [x] 8. Run diagnostics on updated files.
- [x] 9. Run smoke test and argparse help.
- [x] 10. Document direct usage.

## Validation

- main.py diagnostics -> no errors
- scripts/smoke_list_explain_profiles.py -> PASS
- main.py --help -> PASS

## Direct Usage

- List all loaded profiles:
  - python main.py --list-analyzer-profiles

- Explain one concrete profile:
  - python main.py --explain-analyzer-profile spread7-strict

- Explain the currently auto-resolved profile:
  - python main.py --explain-analyzer-profile auto
