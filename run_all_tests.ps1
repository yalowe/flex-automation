# Comprehensive smoke test runner
$sep = "=" * 70
Write-Host $sep
Write-Host "COMPREHENSIVE SMOKE TEST RUN" -ForegroundColor Cyan
Write-Host $sep
Write-Host ""

$tests = @(
    @("smoke_analyzer_cli.py", "Analyzer Profile/Policy CLI"),
    @("smoke_headless_hook_suite.py", "Headless Analyzer Hook"),
    @("smoke_report_parser.py", "Report Parser")
)

$passed = 0
$failed = 0
$i = 1

foreach ($test in $tests) {
    $filename = $test[0]
    $desc = $test[1]
  
    Write-Host "[$i/$($tests.Count)] $desc" -ForegroundColor Yellow -NoNewline
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
