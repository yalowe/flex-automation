# Comprehensive smoke test runner for all phases 5-14
$sep = "=" * 70
Write-Host $sep
Write-Host "COMPREHENSIVE SMOKE TEST RUN (Phases 5-14)" -ForegroundColor Cyan
Write-Host $sep
Write-Host ""

$tests = @(
    @("smoke_headless_monitor_policy.py", "Phase 5 - Policy Wrapper"),
    @("smoke_policy_map_resolution.py", "Phase 7 - Policy Map Resolution"),
    @("smoke_invalid_policy_map.py", "Phase 8 - Invalid Policy Map"),
    @("smoke_analyzer_profiles.py", "Phase 9 - Named Profiles"),
    @("smoke_auto_analyzer_profile.py", "Phase 10 - Auto Profile"),
    @("smoke_analyzer_profiles_file_fallback.py", "Phase 10 - Profile Fallback"),
    @("smoke_invalid_analyzer_profiles_file.py", "Phase 11 - Invalid Config"),
    @("smoke_dry_run_config.py", "Phase 12 - Dry-Run Config"),
    @("smoke_list_explain_profiles.py", "Phase 13 - List/Explain"),
    @("smoke_list_scenarios.py", "Phase 14 - List Scenarios"),
    @("smoke_explain_auto_profile.py", "Phase 14 - Explain Auto")
)

$passed = 0
$failed = 0
$i = 1

foreach ($test in $tests) {
    $filename = $test[0]
    $desc = $test[1]
  
    Write-Host "[$i/11] $desc" -ForegroundColor Yellow -NoNewline
    Write-Host " ... " -NoNewline
  
    $result = & python.exe "scripts\$filename" 2>&1
    $exitCode = $LASTEXITCODE
  
    if ($exitCode -eq 0) {
        Write-Host "[PASS]" -ForegroundColor Green
        $passed++
    }
    else {
        Write-Host "[FAIL]" -ForegroundColor Red
        $failed++
        # Write-Host $result
    }
  
    $i++
}

Write-Host ""
Write-Host $sep
Write-Host "FINAL RESULTS" -ForegroundColor Cyan
Write-Host "  Passed: $passed"
Write-Host "  Failed: $failed"
if ($failed -eq 0) {
    Write-Host "  Status: ALL TESTS PASSED" -ForegroundColor Green
}
else {
    Write-Host "  Status: SOME TESTS FAILED" -ForegroundColor Red
}
Write-Host $sep
