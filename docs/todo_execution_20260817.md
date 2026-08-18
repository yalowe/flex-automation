# Execution TODOs - 2026-08-17

This checklist drives the stabilization and integration flow while keeping existing working programs intact.

## TODO List

- [x] 1. Re-read current runtime files after user edits to avoid merge regressions.
- [x] 2. Stabilize Program 7 (Spread Quantity) expectation path to avoid false exact-match assertions.
- [x] 3. Add Program 7 specific report-based validation guardrails for spread/quantity channels.
- [x] 4. Pass parsed per-channel dosing report into validation layer.
- [x] 5. Harden completed-report parsing for multi-word method/units and variable letter case.
- [x] 6. Keep parser output schema unchanged to avoid breaking existing tests.
- [x] 7. Remove temporary debug prints from runner startup.
- [x] 8. Make scenario summary PASS/FAIL reflect real final outcome.
- [x] 9. Preserve fail-on-anomalies behavior and include it in final scenario status.
- [x] 10. Add runtime configuration options (port, run count, anomaly policy) with safe defaults.
- [x] 11. Add smoke script for parser behavior verification.
- [x] 12. Add smoke script for Program 7 validation path verification.
- [x] 13. Run static error check across modified files and fix issues if found.
- [x] 14. Run smoke scripts and document results.

## Notes

- Safety-first: all new checks for spread/quantity are scoped to Program ID 7 only.
- Backward compatibility: default behavior remains COM5, one run, anomaly gating enabled.
- Smoke results:
  - scripts/smoke_report_parser.py -> PASS
  - scripts/smoke_program7_validation.py -> PASS
