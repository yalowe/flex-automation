# FLEX QA Baseline (Current Implementation)

Date: 2026-08-02
Scope: current codebase behavior only (no assumptions)

## 1) Current Runtime Architecture

- Serial transport: `FlexController` sends raw terminal commands and captures text response.
- Service layer:
  - `IrrigationService`: run/pause/resume/skip/complete program commands and reports.
  - `DeviceService`: read-only metadata/config snapshots.
  - `FlexConfigService`: builds dynamic per-program config from controller responses.
- Parsers:
  - `DOParser`: irrigation valve nominal flow map from `IrrDOMap Info`.
  - `ShiftParser`: program -> recipe + valve list from `Shift Info`.
  - `RecipeParser`: recipe -> 4 dosing-channel blocks from `Recipe Info`.
  - `ReportParser`: completed report extraction + delivered/remaining totals.
- Calculations:
  - `wm_cycle_ms = round(3600000 / flow_lph)` from total valve flow (m3/h -> l/h).
  - `dm_cycle_ms = round(3600000 / dosing_flow_lph)` per enabled channel.
- Test runner:
  - `main.py` runs an infinite nightly loop over predefined scenarios.
  - `ProgramsAndDosings` executes a scenario and validates delivered values against expected values.

## 2) Current Dynamic Configuration Flow

Implemented dynamic pull sequence in `FlexConfigService.get_program_configuration(program_id)`:

1. `irrdomap info` -> parse valve flow per valve id.
2. `shift info` -> parse recipe id + valve list for the program.
3. Sum active valve flows -> total mainline flow.
4. Calculate WM cycle from total flow.
5. `recipe info` -> parse 4 dosing channel slots for that recipe.
6. For each enabled channel:
   - method/units/amount from recipe response
   - dosing flow from static local table (`DOSING_FLOWS`)
   - DM cycle calculation from dosing flow

Returned object fields:
- `program_id`
- `recipe_id`
- `valves`
- `flow`
- `wm_cycle`
- `dosing_channels[channel_id] = {enabled, method, units, amount, flow, dm_cycle}`

## 3) Command Inventory

### 3.1 Commands currently used in code

Read commands (safe read intent):
- `Device Info`
- `IrrProg Info`
- `Shift Info` / `shift info`
- `Recipe Info` / `recipe info`
- `IrrGen Info`
- `IrrAlarm Info`
- `IrrDOMap Info` / `irrdomap info`
- `IrrDIMap Info`
- `IrrAIMap Info`
- `IrrQueue Print`
- `IrrRep Print 0 <program_id>`
- `IrrRep Print 1 <program_id>`
- `Uncomplt RepGet`

Write/control commands (state-changing):
- `IrrCmd Set 0 <program_id>` pause mainline
- `IrrCmd Set 1 <program_id>` resume mainline
- `IrrCmd Set 2 <program_id>` skip shift
- `IrrCmd Set 3 <program_id>` skip program
- `IrrCmd Set 4 <program_id>` manual wait / stop dosing
- `IrrCmd Set 5 <program_id>` run program / start over
- `IrrCmd Set 6 <program_id>` complete program

### 3.2 Commands known from project notes but NOT used by current code

Potentially destructive or sensitive (do not probe blindly):
- `Recipe Config` (writes recipe fields)
- `Recipe Reset` (can reset all recipes)
- `DO Config` (noted reset risk when used without params)
- `Device Reset`
- `IrrQueue Clear`
- `IrrDO Mode`
- `MQUncmp FlashSave`
- `Recipe FlashSave`

Safe policy for this project:
- Treat any `*Config`, `*Reset`, `*Clear`, `FlashSave`, and `Set` command as write-risk until behavior and parameter semantics are verified.
- No write command should be introduced into automation unless:
  1) exact syntax is known,
  2) rollback/recovery is known,
  3) impact scope is known (single program vs global),
  4) approved for QA environment.

## 4) What Already Matches Your Mission

- Configuration is pulled dynamically for valves/program/recipe mapping (no recipe->channel hardcoding).
- WM cycle is calculated from summed active valve flow.
- Per-channel DM cycle is calculated for enabled recipe channels.
- E2E flow runs real controller command path and validates completed report values.

## 5) Critical Gaps vs Target State

1. Scenario expectations are hardcoded in `scenarios.py` (expected water/dosing/remaining), not derived from live program config.
2. Dosing meter flow rates are static local constants (`DOSING_FLOWS`) rather than dynamically read from controller.
3. No simulator auto-configuration service exists yet (WM + DM1..DM4 sync).
4. No command safety registry in code (read vs write vs blocked/unknown).
5. Monitoring/anomaly pipeline is not implemented (AppEvent, alarms, battery, water/dosing event categorization).
6. Alarm test automation framework is not implemented yet.
7. Program wait strategy is mostly fixed sleeps; no robust state-driven polling strategy around finished/report-ready checkpoints.
8. Some model/validator wiring appears incomplete (`ValidationResult` model file is absent in current tree while validators import it).

## 6) Minimal, Safe Implementation Path (No Over-Engineering)

Phase A: Reliability + Dynamic Expectations
- Replace fixed expected values with values derived from live configuration + formulas before each run.
- Add a simple `ProgramRuntimeExpectation` builder function (single module, no framework).
- Replace long blind sleeps with polling on running/completed report state.

Phase B: Safety Guardrails
- Add explicit command registry dictionary:
  - `read_only`, `write_safe_in_qa`, `write_blocked`, `unknown`
- Enforce guard in controller/service: blocked commands raise immediately unless explicit override flag.

Phase C: Simulator Sync
- Add one plain service that receives calculated WM/DM cycles and applies simulator settings.
- Keep mapping explicit: Channel 1->DM1, 2->DM2, 3->DM3, 4->DM4.
- Validate simulator state after apply.

Phase D: Monitoring + Anomaly Detection
- Add lightweight log collector service (file append + event category tags).
- Start with deterministic checks:
  - invalid state transitions,
  - unexpected alarms during normal run,
  - battery recovery with in-range metrics (when battery thresholds are provided).

## 7) Safety Rules To Keep

- Never probe unknown write commands on live/production controllers.
- Prefer read commands for discovery.
- Introduce write/config automation only after command-by-command safety validation.
- Keep services small and direct; avoid abstract frameworks.

## 8) Immediate Next Step Recommendation

Implement Phase A first (dynamic expectation builder + state-based completion polling), because it increases test correctness without changing controller configuration or adding risky commands.

## 9) Implemented In This Iteration

- Added a lightweight monitoring collector service in `services/monitoring_service.py`.
- Wired monitoring into `FlexController.send()` via optional hook (`set_monitoring_service`).
- Enabled monitoring session startup in `main.py` before running tests.

Generated files per run under `logs/<timestamp>/`:
- `raw_commands.txt`
- `app_events.txt`
- `water_meter_events.txt`
- `dosing_events.txt`
- `irrigation_events.txt`
- `alarm_events.txt`
- `battery_events.txt`
- `general_events.txt`
- `anomalies.txt`

Anomaly flags currently detected:
- `command_error` (`Status:Error` lines)
- `battery_recovery_state` (`Battery Recovery` lines)
- `flow_alarm_pattern` (`No Flow`, `Low Flow`, `High Flow`, `flow mismatch` lines)
