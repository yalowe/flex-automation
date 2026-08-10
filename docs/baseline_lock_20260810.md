# Baseline Lock Report

Date: 2026-08-10
Workspace: flex-automation
Baseline anchor commit: e0a2a16
Review mode: strict, read-only (no code edits)

## 1) Locked Change Inventory

Tracked modified files:
- docs/flex_qa_baseline.md
- flex/controller.py
- main.py
- parsers/shift_parser.py
- services/flex_config_service.py
- services/monitoring_service.py
- services/report_parser.py
- tests/program_tests.py
- tests/programs_and_dosings.py

Untracked files:
- docs/flex_set_command_inventory.md
- run_program_test_analysis.py
- services/expectation_builder.py

Per-file tracked diff size (added/deleted):
- docs/flex_qa_baseline.md: +116 / -0
- flex/controller.py: +2 / -0
- main.py: +6 / -1
- parsers/shift_parser.py: +12 / -3
- services/flex_config_service.py: +114 / -2
- services/monitoring_service.py: +151 / -0
- services/report_parser.py: +34 / -0
- tests/program_tests.py: +2621 / -38
- tests/programs_and_dosings.py: +761 / -38

Untracked file line counts:
- docs/flex_set_command_inventory.md: 169
- run_program_test_analysis.py: 579
- services/expectation_builder.py: 194

## 2) Strict Findings (severity ordered)

### Critical

1. Report parser likely drops multi-word units and may miss channel blocks due to strict regex tokens.
- Location: services/report_parser.py lines 12-18.
- Evidence:
  - Method and Units capture only word characters via `(\w+)`, but units can be multi-word (for example, Calculated Quantity).
  - Pattern is case-sensitive for "delivered quantity" and related keys.
- Risk:
  - `parse_dosing_channels` may return incomplete/empty channel data.
  - Downstream validations may pass with reduced evidence or fail non-deterministically.

2. Stale completed report fallback can accept mismatched start-time report and mask run identity drift.
- Location: tests/programs_and_dosings.py lines 462-468.
- Evidence:
  - After repeated mismatches, logic returns latest finalized report when controller is not running.
- Risk:
  - False positives by validating against previous run report.

### High

3. Finish reason acceptance widened to include Stopped, reducing strict E2E completion criteria.
- Location: tests/programs_and_dosings.py line 145.
- Evidence:
  - Assertion now accepts both Completed and Stopped.
- Risk:
  - Aborted/forced-stop runs can be reported as acceptable test outcomes.

4. Shift parser assumes regex match without guard and can throw when line format drifts.
- Location: parsers/shift_parser.py lines 21-22.
- Evidence:
  - `recipe_amount_match` is used directly with `.group(...)` without null check.
- Risk:
  - Runtime exception on minor response formatting variations.

### Medium

5. Entry-point behavior changed to strict anomaly-gated runtime and controller-driven expectations by default.
- Location: main.py lines 183-184.
- Evidence:
  - `fail_on_anomalies=True` and `use_static_expectations=False` are now default path.
- Risk:
  - Operational behavior and pass/fail outcomes changed without feature flag at launch boundary.

6. Primary test engine file underwent very large rewrite with broad behavior expansion.
- Location: tests/program_tests.py (net +2583 lines).
- Evidence:
  - Large helper surface, polling logic, parsing, and validation semantics changed simultaneously.
- Risk:
  - Elevated regression probability and hard-to-isolate failures.

### Low

7. Comment-only debug change in controller.
- Location: flex/controller.py line 49.
- Risk:
  - None functionally at present.

8. Documentation additions are extensive and mostly informational.
- Location: docs/flex_qa_baseline.md and docs/flex_set_command_inventory.md.
- Risk:
  - Low runtime risk; potential staleness risk only.

## 3) Diagnostics Gate

Static editor diagnostics for modified Python files: no syntax/type errors reported.

## 4) Baseline Decision

Status: CONDITIONALLY LOCKED

Interpretation:
- The workspace baseline is now frozen as an audited snapshot (this document + commit anchor + file inventory).
- Migration/refactor should remain blocked until Critical and High findings are explicitly accepted or remediated.

## 5) Recommended Approval Modes

Option A: Hard lock
- Accept this baseline for forensic tracking only.
- No migration work until Critical/High findings are resolved.

Option B: Risk-accepted lock
- Explicitly accept stale-report fallback and Stopped outcome semantics as temporary.
- Proceed with migration while tracking these as known risks.

Option C: Tighten baseline first
- Keep architecture unchanged.
- Apply minimal guard fixes only for parser robustness and stale-report acceptance policy.
