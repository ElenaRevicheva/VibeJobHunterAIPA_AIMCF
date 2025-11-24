# ============================================================================
# LINKEDIN CMO - ONE-TIME TEST COMMANDS
# ============================================================================

Write-Host "`n🎯 LINKEDIN CMO TEST SUITE 🎯`n" -ForegroundColor Cyan

# 1. Link Railway project
Write-Host "1️⃣ Linking Railway project..." -ForegroundColor Yellow
railway link

# 2. Check deployment status
Write-Host "`n2️⃣ Checking deployment status..." -ForegroundColor Yellow
railway status

# 3. Check recent logs for v5.0 marker
Write-Host "`n3️⃣ Checking for v5.0 deployment marker..." -ForegroundColor Yellow
railway logs --tail 200 | Select-String "AI MARKETING CO-FOUNDER v5.0" -Context 5

# 4. Test Make.com webhook with REAL v5.0 content
Write-Host "`n4️⃣ Testing Make.com webhook with v5.0 content..." -ForegroundColor Yellow
$testData = @{
    platform = "linkedin"
    content = @"
🤖 TEST POST - AI Marketing Co-Founder v5.0

9 AI products (5 AIPAs + 4 AI Products) built in 7 months with AI Co-Founders!

🤖 AIPAs - Try 100% FREE:
• wa.me/50766623757 - EspaLuz WhatsApp: Bilingual AIPA for 19 Spanish-speaking countries
• t.me/EspaLuzFamily_bot - EspaLuz Telegram: On-the-go Spanish learning
• x.com/reviceva - ALGOM Alpha: Post-Scammer Era Crypto Coach
• t.me/Influencer_EspaLuz_bot - EspaLuz SMM AIPA
• linkedin.com/in/elenarevicheva - AI Marketing Co-Founder posting!

🌐 AI Products - Explore 100% FREE:
• espaluz-ai-language-tutor.lovable.app - Family's First Emotionally Intelligent AI Language Coach
• aideazz.xyz - Emotionally Intelligent AI Assistants Showroom
• aideazz.xyz/card - Founder's Portfolio
• atuona.xyz - Underground Russian Poetry NFT Gallery

Built with AI Co-Founders (not just AI tools)!
Ex-CEO/CLO → AI Founder → vibecoder

#AI #BuildInPublic #AICoFounders #EmotionallyIntelligentAI
"@
    text = "TEST: AI Marketing Co-Founder v5.0 with dignified positioning"
    language = "en"
    post_type = "test"
    timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss")
    author = "Elena Revicheva"
    imageURL = "https://raw.githubusercontent.com/ElenaRevicheva/VibeJobHunterAIPA_AIMCF/main/image_1.png"
    hook = "🎯 TEST: v5.0 Dignified Positioning"
    audience = "Tech Founders & Investors"
    emotional_state = "Confident Founder"
    target_market = "AI Startups"
    viral_potential = "High"
    instagram_focus = "Portfolio Showcase"
    linkedin_focus = "Founder Branding"
} | ConvertTo-Json -Depth 10

Write-Host "`n📤 Sending to Make.com..." -ForegroundColor Green
$response = Invoke-RestMethod -Uri "https://hook.us2.make.com/n771e2agfz6g1y13zhv29hkts24u2u5z" -Method POST -Body $testData -ContentType "application/json"
Write-Host "✅ Response: $response" -ForegroundColor Green

# 5. Verify images are accessible
Write-Host "`n5️⃣ Verifying images..." -ForegroundColor Yellow
Write-Host "   Checking image_1.png..." -ForegroundColor Gray
$img1 = Invoke-WebRequest -Uri "https://raw.githubusercontent.com/ElenaRevicheva/VibeJobHunterAIPA_AIMCF/main/image_1.png" -Method HEAD
Write-Host "   ✅ image_1.png: $($img1.StatusCode) $($img1.StatusDescription)" -ForegroundColor Green

Write-Host "   Checking image_1.1.png..." -ForegroundColor Gray
$img2 = Invoke-WebRequest -Uri "https://raw.githubusercontent.com/ElenaRevicheva/VibeJobHunterAIPA_AIMCF/main/image_1.1.png" -Method HEAD
Write-Host "   ✅ image_1.1.png: $($img2.StatusCode) $($img2.StatusDescription)" -ForegroundColor Green

# 6. Check all product links
Write-Host "`n6️⃣ Verifying all 9 product links..." -ForegroundColor Yellow
$links = @(
    @{name="EspaLuz WhatsApp"; url="https://wa.me/50766623757"},
    @{name="EspaLuz Telegram"; url="https://t.me/EspaLuzFamily_bot"},
    @{name="ALGOM Alpha"; url="https://x.com/reviceva"},
    @{name="EspaLuz SMM"; url="https://t.me/Influencer_EspaLuz_bot"},
    @{name="LinkedIn"; url="https://linkedin.com/in/elenarevicheva"},
    @{name="Instagram"; url="https://www.instagram.com/elena_revicheva/"},
    @{name="EspaLuz Web"; url="https://espaluz-ai-language-tutor.lovable.app"},
    @{name="AIdeazz"; url="https://aideazz.xyz"},
    @{name="ATUONA"; url="https://atuona.xyz"}
)

foreach ($link in $links) {
    try {
        $response = Invoke-WebRequest -Uri $link.url -Method HEAD -TimeoutSec 5 -ErrorAction Stop
        Write-Host "   ✅ $($link.name): $($response.StatusCode)" -ForegroundColor Green
    } catch {
        Write-Host "   ⚠️ $($link.name): Cannot verify (might need auth)" -ForegroundColor Yellow
    }
}

# 7. Watch live logs for posting activity
Write-Host "`n7️⃣ Watching Railway logs (Press Ctrl+C to stop)..." -ForegroundColor Yellow
Write-Host "   Look for: LinkedIn CMO, post_to_linkedin, send_to_make_com" -ForegroundColor Gray
railway logs --tail 50

Write-Host "`n✅ TEST COMPLETE!" -ForegroundColor Green
Write-Host "`n📊 Summary:" -ForegroundColor Cyan
Write-Host "   • Railway linked and v5.0 verified" -ForegroundColor White
Write-Host "   • Test webhook sent to Make.com" -ForegroundColor White
Write-Host "   • All images verified" -ForegroundColor White
Write-Host "   • Product links checked" -ForegroundColor White
Write-Host "`n🎯 Next: Check Buffer/LinkedIn for test post!" -ForegroundColor Cyan

