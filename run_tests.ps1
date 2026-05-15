# run_tests.ps1 - SynthTrade Unified Test Suite
# Runs both Backend (Pytest) and Frontend (Jest) tests.

$ErrorActionPreference = "Continue"
$OverallSuccess = $true

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   SynthTrade Unified Test Runner" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Backend Tests
Write-Host "`n[1/2] Running Backend Tests (pytest)..." -ForegroundColor Yellow
Set-Location "synthtrade/backend"
& "../../.venv/Scripts/pytest"
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Backend tests failed!" -ForegroundColor Red
    $OverallSuccess = $false
} else {
    Write-Host "✅ Backend tests passed!" -ForegroundColor Green
}
Set-Location "../../"

# 2. Frontend Tests
Write-Host "`n[2/2] Running Frontend Tests (npm test)..." -ForegroundColor Yellow
Set-Location "synthtrade/frontend/synthtrade-ui"
npm run test:ci
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Frontend tests failed!" -ForegroundColor Red
    $OverallSuccess = $false
} else {
    Write-Host "✅ Frontend tests passed!" -ForegroundColor Green
}
Set-Location "../../../"

Write-Host "`n========================================" -ForegroundColor Cyan
if ($OverallSuccess) {
    Write-Host "🎉 ALL TESTS PASSED!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "⚠️  SOME TESTS FAILED. Check details above." -ForegroundColor Yellow
    exit 1
}
