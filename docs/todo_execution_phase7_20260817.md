# Execution TODOs Phase 7 - 2026-08-17

Phase 7 adds per-program analyzer policy mapping (for example Program 7 strict, others safe).

## TODO List

- [x] 1. Re-read current main and hook files after user edits.
- [x] 2. Add policy-map resolver in scenario hook.
- [x] 3. Add wildcard fallback policy support.
- [x] 4. Keep behavior backward compatible when map is empty.
- [x] 5. Add CLI flag for analyzer policy map in main.
- [x] 6. Add CLI flag for analyzer default policy in main.
- [x] 7. Auto-wire policy-map env vars when map is provided.
- [x] 8. Add smoke test for policy map resolution.
- [x] 9. Run diagnostics and smoke tests.
- [x] 10. Document direct CLI usage examples.

## Notes

- Mapping format: "7:strict,8:lab,\*:safe"
- Specific program IDs override wildcard.
- Hook placeholder {policy} is resolved per scenario.
- Validation results:
	- main.py diagnostics -> no errors
	- tests/programs_and_dosings.py diagnostics -> no errors
	- scripts/smoke_policy_map_resolution.py -> PASS
	- main.py --help -> PASS

## Direct CLI Usage

- Program-specific map with strict policy for Program 7 and safe fallback:
	- python main.py --analyzer-policy safe --analyzer-policy-map "7:strict,*:safe"

- Map including lab policy for Program 8:
	- python main.py --analyzer-policy safe --analyzer-policy-map "7:strict,8:lab,*:safe"

- Change default fallback policy when wildcard is omitted:
	- python main.py --analyzer-policy safe --analyzer-policy-map "7:strict" --analyzer-default-policy lab
