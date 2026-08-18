# Phase 14: Inspection Commands - List Scenarios & Auto-Profile Explanation

**Status**: ✅ COMPLETE  
**Date**: 2026-08-17  
**Scope**: Add two convenience inspection commands for improved CLI visibility

## Summary

Added two additional inspection commands to complete the visibility/inspection layer:

1. `--list-scenarios`: Display all active test scenarios with program IDs
2. `--explain-auto-profile`: Convenience wrapper to explain the auto-resolved profile

Both commands exit cleanly after printing their output, following the existing inspection command pattern.

## Changes Made

### main.py

**New Flags** (parse_args):

- `--list-scenarios` (BooleanOptionalAction): Lists active scenarios and exits
- `--explain-auto-profile` (BooleanOptionalAction): Explains auto-resolved profile and exits

**New Functions**:

1. `list_scenarios()`:
   - Iterates SCENARIOS and displays each scenario name + program_id
   - Formatted output with consistent column width
2. `explain_auto_profile(args: Namespace)`:
   - Calls existing explain_analyzer_profile() with "auto" as profile name
   - Lets existing logic handle resolution of "auto" to concrete profile

**Updated main() function**:

- Added two new if-checks BEFORE apply_analyzer_profile()
- Both early-exit after printing output
- Execution order:
  1. `--list-scenarios` check → list_scenarios() → return
  2. `--explain-auto-profile` check → explain_auto_profile() → return
  3. (rest of existing flow)

## CLI Integration

### Help Text

```
  --list-scenarios, --no-list-scenarios
                        List active scenarios and exit (default: False)
  --explain-auto-profile, --no-explain-auto-profile
                        Explain the auto-resolved analyzer profile and exit (default: False)
```

### Usage Examples

```bash
# List active scenarios
python main.py --list-scenarios

# Explain what auto profile resolves to (with Program 7 active → spread7-strict)
python main.py --explain-auto-profile
```

### Sample Output

**--list-scenarios**:

```
========== ACTIVE SCENARIOS ==========
  Spread By Quantity                  (Program ID 7)
======================================
```

**--explain-auto-profile** (with Program 7 active):

```
========== ANALYZER PROFILE ==========
Requested Name   : auto
Resolved Name    : spread7-strict
Policy           : safe
Policy Map       : 7:strict,*:safe
Default Policy   : safe
======================================
```

## Validation

### Smoke Tests Created

1. **smoke_list_scenarios.py**:
   - Verifies --list-scenarios displays all scenarios
   - Confirms output format and scenario names/IDs
   - Status: ✅ PASS

2. **smoke_explain_auto_profile.py**:
   - Verifies --explain-auto-profile resolves to active profile
   - Confirms "auto" is shown as requested, "spread7-strict" as resolved
   - Confirms all profile details displayed correctly
   - Status: ✅ PASS

### Help Output

- ✅ Both flags present in main.py --help
- ✅ Descriptions accurate
- ✅ Both support --no-\* negation

## Architecture Notes

**Design Pattern Consistency**:

- Follows existing inspection command pattern (--list-analyzer-profiles, --explain-analyzer-profile, --dry-run-config)
- All inspection commands are BooleanOptionalAction (no arguments required)
- All exit cleanly before hardware connection
- All positioned early in main() to avoid unnecessary processing

**Code Reuse**:

- `explain_auto_profile()` leverages existing `explain_analyzer_profile()`
- `list_scenarios()` uses existing SCENARIOS list from scenarios module
- No new dependencies or utilities added

**Execution Flow**:

```
main.py CLI execution
├─ --list-scenarios? → list_scenarios() → exit
├─ --explain-auto-profile? → explain_auto_profile() → exit
├─ apply_analyzer_profile()  [Phase 5 feature]
├─ --list-analyzer-profiles? → list_analyzer_profiles() → exit  [Phase 13]
├─ --explain-analyzer-profile? → explain_analyzer_profile() → exit  [Phase 13]
├─ --dry-run-config? → print_effective_config() → exit  [Phase 12]
└─ continue to hardware connection & run
```

## Files Changed

1. main.py: Added 3 functions, 2 CLI flags, updated main()
2. scripts/smoke_list_scenarios.py: NEW - validates --list-scenarios
3. scripts/smoke_explain_auto_profile.py: NEW - validates --explain-auto-profile

## Next Steps / Future Enhancements

Potential future improvements (not implemented):

- `--list-profiles` as shorthand for `--list-analyzer-profiles`
- `--profile-by-scenario NAME` to select profile by scenario name instead of "auto"
- Config file support for custom profile lists (INI, TOML formats)
- JSON export of scenarios/profiles for integration with other tools

---

**Phase 14 Completion Checklist**:

- ✅ Feature implemented (2 inspection commands)
- ✅ Smoke tests created and passing (2/2)
- ✅ Help text updated and verified
- ✅ Code follows existing patterns
- ✅ Documentation complete

**Overall Status**: Phases 5-14 complete and validated. All 14+ smoke tests passing.
