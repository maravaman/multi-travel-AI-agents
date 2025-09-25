# FFmpeg Installation Script for Windows
# This script helps install ffmpeg for the Travel AI System audio transcription feature

Write-Host "🎤 FFmpeg Installation for Travel AI System" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")

if (-not $isAdmin) {
    Write-Host "⚠️  This script needs to be run as Administrator" -ForegroundColor Yellow
    Write-Host "   Please:" -ForegroundColor Yellow
    Write-Host "   1. Right-click PowerShell" -ForegroundColor Yellow
    Write-Host "   2. Select 'Run as Administrator'" -ForegroundColor Yellow
    Write-Host "   3. Run this script again" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check what package managers are available
$chocoAvailable = Get-Command choco -ErrorAction SilentlyContinue
$wingetAvailable = Get-Command winget -ErrorAction SilentlyContinue

Write-Host "📋 Checking available package managers..." -ForegroundColor Green

if ($chocoAvailable) {
    Write-Host "✅ Chocolatey found" -ForegroundColor Green
    Write-Host "📦 Installing ffmpeg via Chocolatey..." -ForegroundColor Green
    try {
        choco install ffmpeg -y
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ FFmpeg installed successfully via Chocolatey!" -ForegroundColor Green
        } else {
            throw "Chocolatey installation failed"
        }
    } catch {
        Write-Host "❌ Chocolatey installation failed: $($_.Exception.Message)" -ForegroundColor Red
        $chocoAvailable = $false
    }
}

if (-not $chocoAvailable -and $wingetAvailable) {
    Write-Host "✅ Winget found" -ForegroundColor Green
    Write-Host "📦 Installing ffmpeg via Winget..." -ForegroundColor Green
    try {
        winget install ffmpeg
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ FFmpeg installed successfully via Winget!" -ForegroundColor Green
        } else {
            throw "Winget installation failed"
        }
    } catch {
        Write-Host "❌ Winget installation failed: $($_.Exception.Message)" -ForegroundColor Red
        $wingetAvailable = $false
    }
}

if (-not $chocoAvailable -and -not $wingetAvailable) {
    Write-Host "⚠️  No package managers found" -ForegroundColor Yellow
    Write-Host "   Manual installation required:" -ForegroundColor Yellow
    Write-Host "   1. Visit https://ffmpeg.org/download.html" -ForegroundColor Yellow
    Write-Host "   2. Download Windows build" -ForegroundColor Yellow
    Write-Host "   3. Extract to C:\ffmpeg" -ForegroundColor Yellow
    Write-Host "   4. Add C:\ffmpeg\bin to your PATH environment variable" -ForegroundColor Yellow
    Write-Host "   5. Restart your command prompt and applications" -ForegroundColor Yellow
}

# Test if ffmpeg is now available
Write-Host "🧪 Testing ffmpeg installation..." -ForegroundColor Green
try {
    $ffmpegTest = & ffmpeg -version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ FFmpeg is working correctly!" -ForegroundColor Green
        Write-Host "🎉 You can now use audio transcription in the Travel AI System" -ForegroundColor Green
    } else {
        throw "FFmpeg test failed"
    }
} catch {
    Write-Host "❌ FFmpeg is not working yet" -ForegroundColor Red
    Write-Host "   You may need to:" -ForegroundColor Red
    Write-Host "   - Restart your command prompt/PowerShell" -ForegroundColor Red
    Write-Host "   - Restart your applications" -ForegroundColor Red
    Write-Host "   - Check your PATH environment variable" -ForegroundColor Red
}

Write-Host ""
Write-Host "📝 Next steps:" -ForegroundColor Cyan
Write-Host "   1. Close this window" -ForegroundColor White
Write-Host "   2. Restart your Python application" -ForegroundColor White
Write-Host "   3. Try audio transcription again" -ForegroundColor White

Read-Host "Press Enter to close"