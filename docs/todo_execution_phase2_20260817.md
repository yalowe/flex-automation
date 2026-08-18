# Execution TODOs Phase 2 - 2026-08-17

Focused on safe staged integration with Flex_tester while preserving current stable runs.

## TODO List

- [x] 1. Re-read current main/report/validation files before new edits.
- [x] 2. Add optional WM sync integration before controller connect.
- [x] 3. Keep WM sync disabled by default (feature-flag behavior).
- [x] 4. Add strict/non-strict WM sync failure policy.
- [x] 5. Add configurable serial baud in runner arguments.
- [x] 6. Keep default behavior backward compatible (COM5, 115200, runs=1).
- [x] 7. Print run settings including sync flags for observability.
- [x] 8. Run static diagnostics on modified files.
- [x] 9. Run no-hardware smoke check for CLI parsing/help.
- [x] 10. Document sample commands for enabling sync safely.

## Notes

- WM sync uses Flex_tester/sync_wm_settings_to_board.py and wm_settings.json.
- Sync runs before opening the main controller serial connection.
- In non-strict mode, sync failures emit warning and continue.
- Validation results:
	- main.py diagnostics -> no errors
	- main.py --help smoke -> PASS

## Safe Usage Examples

- Default behavior (unchanged):
	- python main.py
- Enable WM sync but continue if sync fails:
	- python main.py --wm-sync
- Enable WM sync and fail fast on sync errors:
	- python main.py --wm-sync --wm-sync-strict
- Use custom settings file:
	- python main.py --wm-sync --wm-sync-settings Flex_tester/wm_settings.json
