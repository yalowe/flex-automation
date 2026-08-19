param(
    [string]$Port = "COM5",
    [int]$Baud = 115200,
    [int]$Runs = 1,
    [string]$Python = ".\.venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$results = Join-Path $root "allure-results\$stamp"
New-Item -ItemType Directory -Force -Path $results | Out-Null

Write-Host "Starting FLEX hardware pytest run: port=$Port baud=$Baud runs=$Runs"
& $Python -m pytest -m hardware --flex-port $Port --flex-baud $Baud --flex-runs $Runs --alluredir $results
$pytestExitCode = $LASTEXITCODE

$report = Join-Path $root "allure-report\$stamp"
if (Get-Command allure -ErrorAction SilentlyContinue) {
    & allure generate $results -o $report --clean
    Write-Host "Allure report: $report\index.html"
}
else {
    Write-Warning "Allure CLI not found. Install it separately, then run: allure generate $results -o $report --clean"
}

exit $pytestExitCode