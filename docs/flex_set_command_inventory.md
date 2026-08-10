# FLEX Configuration Command Verification Inventory

Date: 2026-08-03
Scope: command discovery and safety verification only
Decision rule: only commands with direct execution evidence are marked verified
Execution status: LIVE PROOF BLOCKED CURRENTLY (COM5 access denied)

## 1) Evidence used

- Executed command logs:
  - `logs/20260802_225239/raw_commands.txt`
  - `logs/20260802_230010/raw_commands.txt`
  - `logs/20260802_230202/raw_commands.txt`
- Existing implementation and docs:
  - `services/irrigation_service.py`
  - `docs/flex_qa_baseline.md`
  - `/memories/repo/flex-commands.md`

Observed executed writable commands from raw logs:
- `IrrCmd Set 5 3` (2 executions)
- `IrrCmd Set 6 3` (1 execution)

No execution evidence found yet for:
- `Recipe Config`, `Recipe Reset`, `DO Config`, `DI Config`, `AI Config`
- `IrrProg Config`, `Shift Config`, `IrrGen Config`, `IrrAlarm Config`
- `IrrDO Mode`, `IrrQueue Clear`, `Device Reset`, `Recipe FlashSave`, `MQUncmp FlashSave`

Command help syntax is available (from controller command list), but still needs live proof.

## 2) Verified command records (proven by execution evidence)

### 2.1 Run Program

- Exact syntax: `IrrCmd Set 5 <program_id>`
- Required parameters:
  - `program_id` integer
- Before/after verification evidence:
  - command success line: `logs/20260802_225239/raw_commands.txt:305`
  - state transition seen: `logs/20260802_225239/raw_commands.txt:343`
  - running report block: `logs/20260802_225239/raw_commands.txt:353`
- Rollback procedure:
  - use `IrrCmd Set 3 <program_id>` to skip/stop active run
  - if still running, use `IrrCmd Set 2 <program_id>` (shift skip) until clear
- Risk level: Medium (changes runtime state, but not persistent config)
- Safe for automation: Yes, for test execution control

### 2.2 Complete Program

- Exact syntax: `IrrCmd Set 6 <program_id>`
- Required parameters:
  - `program_id` integer
- Before/after verification evidence:
  - command success line: `logs/20260802_230202/raw_commands.txt:305`
  - report still shows `Program Id: 3 ... State: Running`: `logs/20260802_230202/raw_commands.txt:467`
  - report includes `Finish reason: Completed`: `logs/20260802_230202/raw_commands.txt:481`
- Rollback procedure:
  - if state does not clear, issue `IrrCmd Set 3 <program_id>` then `IrrCmd Set 2 <program_id>` fallback
- Risk level: Medium
- Safe for automation: Conditional. Not reliable as sole completion mechanism.

## 3) Entity-by-entity writable command inventory

This section is intentionally strict. If syntax is not proven by execution logs or controlled manual proof, it remains unverified.

| Entity | Candidate writable command(s) | Exact syntax status | Required parameters status | Before/after proof status | Rollback status | Risk level | Safe for automation now |
|---|---|---|---|---|---|---|---|
| Programs | `IrrCmd Set 5`, `IrrCmd Set 6`, `IrrCmd Set 3`, `IrrCmd Set 2`; possible `IrrProg Config` (unproven) | Verified for `IrrCmd Set X <program_id>`; unverified for config command | `program_id` proven for `IrrCmd Set`; config params unknown | Proven for run-state control; no proof for persistent program configuration | Proven for runtime rollback (`Set 3` then `Set 2`) | Medium for runtime control; High for unknown config | Runtime control: Yes. Persistent program config: No |
| Recipes | `Recipe Config`, `Recipe Reset`, `Recipe FlashSave` | Syntax known from help, not executed in this campaign | Params known from help, not validated | No direct execution proof yet | Planned rollback defined, not executed | High to Very High | No |
| Irrigation Valves | `IrrDO Mode` (runtime), `DO Config` (electrical config) | Syntax known from help, not executed in this campaign | Params known from help, not validated | No direct execution proof yet | Planned rollback defined, not executed | Medium (mode) to High (config) | No |
| Water Meter | `DI Config` / `DI Enable` on DI1 | Syntax known from help, not executed in this campaign | Params known from help, not validated | No direct execution proof yet | Planned rollback defined, not executed | High | No |
| Dosing Channels | `Recipe Config` (channel-level dosing), optional `IrrDO Mode` for DO behavior | Syntax known from help, not executed in this campaign | Params known from help, not validated | No direct execution proof yet | Planned rollback defined, not executed | High | No |
| Dosing Meters | `DI Config` / `DI Enable` on DI2..DI5 | Syntax known from help, not executed in this campaign | Params known from help, not validated | No direct execution proof yet | Planned rollback defined, not executed | High | No |
| Alerts | No explicit `IrrAlarm Config` shown in help list | Unverified | Unknown | No direct execution proof | Unknown | High | No |
| Sensors | `AI Config`, `AI Enable`, `AI Reset` (and optionally `AIMng Config`) | Syntax known from help, not executed in this campaign | Params known from help, not validated | No direct execution proof yet | Planned rollback defined, not executed | Medium to High | No |

## 4) Exact write syntax and parameter format (from controller help)

These syntax templates come from the device command list and are NOT marked verified until live proof succeeds.

### Programs

- `IrrCmd Set <command> <program_id> [run_with_dosing] [ml_pause_reason]`
  - `command`: `0` Pause, `1` Resume, `2` Skip Shift, `3` Skip Program, `4` Manual Wait, `5` Manual Force, `6` Complete, `7` Stop Dosing
  - `program_id`: program number
  - `run_with_dosing` (optional): bool
  - `ml_pause_reason` (optional): `0..5`

### Recipes

- `Recipe Config [recipe_no] [active] [dosing_channel] [dosing_method] [dosing_units] [dm_enabled] [amount]`
  - `recipe_no`: `0` all or `1..8`
  - `active`: `0/1`
  - `dosing_channel`: `0` all or `1..4`
  - `dosing_method`: `0` Bulk, `1` Spread, `2` Proportional
  - `dosing_units`: `0` Time, `1` Quantity, `2` Calculated Quantity
  - `dm_enabled`: `0/1`
  - `amount`: uint
- `Recipe Reset [recipe_no]`
- `Recipe FlashSave`

### Irrigation Valves

- `IrrDO Mode [valve_no] [manual_mode]`
  - `valve_no`: `0` all or `1..PumpML_DEVICE_DO_MAX`
  - `manual_mode`: `0` Auto, `1` Close, `2` Open
- `DO Config [do_no] [voltage]`
  - `do_no`: `0` all or `1..16`
  - `voltage`: `0` or `12000..15000`

### Water Meter and Dosing Meters (DI)

- `DI Config [di_no] [mode] [voltage] [debounce_delay] [type]`
  - `di_no`: `0` all or `1..8`
  - `mode`: `0` NO, `1` NC, `2` Switching, `3` Frequency
  - `voltage`: `0`, `3300`, `12000`, `24000`
  - `debounce_delay`: `0..100` ms
  - `type`: `0` Dry Contact, `1` Active
- `DI Enable [di_no] [enable]`
- `DI Reset [di_no]`

### Alerts

- No explicit alert write command appears in provided help list.
- `IrrAlarm Info` is read-only in current evidence.

### Sensors

- `AI Config [ai_no] [mode] [voltage] [period_ms] [stabilization_ms] [divider] [avg_samples]`
- `AI Enable [ai_no] [enable]`
- `AI Reset [ai_no]`
- Optional manager path:
  - `AIMng Config [ai_no] [mode] [voltage] [window_ms] [stabilization_ms] [divider] [samples]`

## 5) Controlled reversible proof plan per entity (ready to execute)

All tests below are designed to be reversible and minimal-impact. They remain UNVERIFIED until executed successfully.

### Programs (runtime control)

- Before: `IrrProg Info` and `IrrRep Print 0 <program_id>`
- Write: `IrrCmd Set 5 <program_id>`
- After: confirm transition to Running
- Rollback: `IrrCmd Set 3 <program_id>`; if needed `IrrCmd Set 2 <program_id>`
- Status: PARTIALLY VERIFIED (runtime only)

### Recipes

- Before: `Recipe Info` snapshot for one recipe/channel
- Write: `Recipe Config <r> 1 <ch> <method> <units> <dm_enable> <new_amount>`
- After: `Recipe Info` shows new amount/method/units
- Rollback: same command with original values; optional `Recipe FlashSave` policy validation
- Status: UNVERIFIED

### Irrigation Valves

- Before: `IrrDOMap Info`
- Write: `IrrDO Mode <valve> 1` (force close) or `2` (force open)
- After: `IrrDOMap Info` reflects manual state/mode change
- Rollback: `IrrDO Mode <valve> 0` (auto)
- Status: UNVERIFIED

### Water Meter

- Before: `DI Info` and `IrrDIMap Info` for DI1
- Write: `DI Enable 1 0` (disable DI1)
- After: `DI Info` / map shows disabled state
- Rollback: `DI Enable 1 1`
- Status: UNVERIFIED

### Dosing Channels

- Before: `Recipe Info` and `IrrDOMap Info` for target channel
- Write: `Recipe Config <r> 1 <channel> <method> <units> <dm_enable> <new_amount>`
- After: `Recipe Info` reflects channel change
- Rollback: restore original channel values with `Recipe Config`
- Status: UNVERIFIED

### Dosing Meters

- Before: `DI Info` for DI2..DI5 and `IrrDIMap Info`
- Write: `DI Enable <di> 0`
- After: DI state changes for that meter input
- Rollback: `DI Enable <di> 1`
- Status: UNVERIFIED

### Alerts

- Before: `IrrAlarm Info`
- Write: no proven alert write command in current list
- After: N/A
- Rollback: N/A
- Status: UNVERIFIED (blocked by missing write command)

### Sensors

- Before: `AI Info` (or `AIMng Info`)
- Write: `AI Config <ai> <mode> <voltage> <period> <stab> <divider> <avg>`
- After: `AI Info` reflects changes
- Rollback: restore original params using `AI Config` or `AI Reset <ai>`
- Status: UNVERIFIED

## 6) Current safe scope for automation (today)

Safe and proven today:
- Use `IrrCmd Set` family for run control only.
- Keep using read commands (`IrrProg Info`, `Shift Info`, `Recipe Info`, `IrrDOMap Info`, `IrrDIMap Info`, `IrrAIMap Info`, `IrrAlarm Info`) for discovery and verification.

Not safe yet:
- Any persistent configuration write command without proven syntax, side effects, and rollback.

## 7) Verification protocol to unlock each unverified entity

Per command candidate, collect and store this exact proof package before allowing automation use:
1. Exact command string used.
2. Parameter meaning and allowed range.
3. Pre-state snapshot (`* Info`).
4. Post-state snapshot (`* Info`) confirming only intended fields changed.
5. Rollback command and rollback verification snapshot.
6. Persistence behavior proof (survives reset or requires flash save).

Until this package exists, command stays blocked for automated configuration.
