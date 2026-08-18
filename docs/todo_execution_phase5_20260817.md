# Execution TODOs Phase 5 - 2026-08-17

Phase 5 adds policy presets for headless monitoring to simplify hook usage.

## TODO List

- [x] 1. Add policy wrapper script around headless analyzer.
- [x] 2. Implement safe policy defaults.
- [x] 3. Implement strict policy defaults.
- [x] 4. Implement lab policy defaults.
- [x] 5. Support per-flag overrides over presets.
- [x] 6. Keep backward compatibility (no runner behavior change by default).
- [x] 7. Add smoke script validating safe/strict/lab outcomes.
- [x] 8. Run diagnostics on new scripts.
- [x] 9. Run policy smoke script.
- [x] 10. Document hook command example using policy wrapper.

## Notes

- Policy script: scripts/headless_monitor_policy.py
- Smoke script: scripts/smoke_headless_monitor_policy.py
- Validation results:
  - scripts/headless_monitor_policy.py diagnostics -> no errors
  - scripts/smoke_headless_monitor_policy.py -> PASS

## Hook Examples

- Safe policy (recommended start):
  - set FLEX_HEADLESS_ANALYZER_CMD=python scripts/headless_monitor_policy.py --policy safe --session-dir "{session_dir}" --scenario-name "{scenario_name}" --program-id {program_id} --anomaly-count {anomaly_count}
  - python main.py

- Strict policy:
  - set FLEX_HEADLESS_ANALYZER_CMD=python scripts/headless_monitor_policy.py --policy strict --session-dir "{session_dir}" --scenario-name "{scenario_name}" --program-id {program_id} --anomaly-count {anomaly_count}
  - set FLEX_HEADLESS_ANALYZER_STRICT=true
  - python main.py

- Lab policy (least restrictive):
  - set FLEX_HEADLESS_ANALYZER_CMD=python scripts/headless_monitor_policy.py --policy lab --session-dir "{session_dir}" --scenario-name "{scenario_name}" --program-id {program_id} --anomaly-count {anomaly_count}
  - python main.py
