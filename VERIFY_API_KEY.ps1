# 🔍 Verify New Anthropic API Key is Working

Write-Host "`n🔑 CHECKING NEW ANTHROPIC API KEY...`n" -ForegroundColor Cyan

# 1. Check Railway deployment status
Write-Host "1️⃣ Checking Railway deployment..." -ForegroundColor Yellow
railway status

# 2. Get latest logs (look for new container start)
Write-Host "`n2️⃣ Getting latest logs (look for new deployment)..." -ForegroundColor Yellow
railway logs --tail 100 | Select-String "Starting Container" -Context 2

# 3. Check for Claude API errors (should be NONE now!)
Write-Host "`n3️⃣ Checking for Claude API errors..." -ForegroundColor Yellow
$errors = railway logs --tail 200 | Select-String "claude-3-5-sonnet|404|not_found_error"
if ($errors) {
    Write-Host "   ❌ Still seeing Claude errors:" -ForegroundColor Red
    $errors
} else {
    Write-Host "   ✅ No Claude API errors found!" -ForegroundColor Green
}

# 4. Check for AI Co-Founder mode activation
Write-Host "`n4️⃣ Checking AI Co-Founder mode..." -ForegroundColor Yellow
railway logs --tail 100 | Select-String "AI CO-FOUNDER MODE ACTIVATED" -Context 2

# 5. Check if LinkedIn CMO initialized successfully
Write-Host "`n5️⃣ Checking LinkedIn CMO initialization..." -ForegroundColor Yellow
railway logs --tail 100 | Select-String "LinkedInCMO initialized successfully"

Write-Host "`n✅ VERIFICATION COMPLETE!" -ForegroundColor Green
Write-Host "`nIf you see:" -ForegroundColor Cyan
Write-Host "   ✅ 'AI CO-FOUNDER MODE ACTIVATED'" -ForegroundColor White
Write-Host "   ✅ 'claude-3-5-sonnet' mentioned (no 404 errors)" -ForegroundColor White
Write-Host "   ✅ 'LinkedInCMO initialized successfully'" -ForegroundColor White
Write-Host "`nThen your API key is working! 🎉" -ForegroundColor Green
