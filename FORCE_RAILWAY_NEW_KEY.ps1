# 🔑 Force Railway to Use New API Key

Write-Host "`n🚨 FORCING RAILWAY TO USE NEW API KEY 🚨`n" -ForegroundColor Red

# 1. Check current variable
Write-Host "1️⃣ Checking current ANTHROPIC_API_KEY in Railway..." -ForegroundColor Yellow
railway variables | Select-String "ANTHROPIC"

# 2. Set the new API key (COPY YOUR FULL KEY HERE!)
Write-Host "`n2️⃣ Setting NEW API key..." -ForegroundColor Yellow
Write-Host "⚠️ PASTE YOUR FULL KEY: sk-ant-api03-ng-...qQAA" -ForegroundColor Red
$newKey = Read-Host "Enter your FULL Anthropic API key"

railway variables set ANTHROPIC_API_KEY="$newKey"

# 3. Verify it was set
Write-Host "`n3️⃣ Verifying new key is set..." -ForegroundColor Yellow
railway variables | Select-String "ANTHROPIC"

# 4. Force redeploy
Write-Host "`n4️⃣ Forcing Railway redeploy..." -ForegroundColor Yellow
railway up --detach

Write-Host "`n✅ Done! Railway will rebuild with NEW API key!" -ForegroundColor Green
Write-Host "⏰ Wait 2-3 minutes, then check logs for NO 404 errors!" -ForegroundColor Cyan
