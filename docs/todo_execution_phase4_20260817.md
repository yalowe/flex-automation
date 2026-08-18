# Execution TODOs Phase 4 - 2026-08-17

Phase 4 implements a real monitoring analyzer script for headless hook execution.

## TODO List

- [x] 1. Re-read current hook integration and monitoring file formats.
- [x] 2. Create standalone analyzer script for session directory checks.
- [x] 3. Parse latest scenario summary from scenario_monitoring_summary.txt.
- [x] 4. Add anomaly threshold policy controls.
- [x] 5. Add minimum activity checks (device/wm/valve events).
- [x] 6. Add blocked-anomaly type detection from anomalies.txt.
- [x] 7. Keep CLI explicit and safe (no implicit behavior changes in runner).
- [x] 8. Add smoke script that validates PASS and FAIL paths.
- [x] 9. Run diagnostics and smoke scripts.
- [x] 10. Document hook command template for real analyzer usage.

## Notes

- Analyzer script: scripts/headless_monitor_analyzer.py
- Smoke script: scripts/smoke_headless_monitor_analyzer.py
- Validation results:
	- scripts/headless_monitor_analyzer.py diagnostics -> no errors
	- scripts/smoke_headless_monitor_analyzer.py -> PASS

## Hook Command Example

- Non-strict hook with analyzer policy:
	- set FLEX_HEADLESS_ANALYZER_CMD=python scripts/headless_monitor_analyzer.py --session-dir "{session_dir}" --scenario-name "{scenario_name}" --program-id {program_id} --anomaly-count {anomaly_count} --max-anomalies 0 --min-device-events 1
	- python main.py

- Strict hook mode:
	- set FLEX_HEADLESS_ANALYZER_STRICT=true
	- python main.py
