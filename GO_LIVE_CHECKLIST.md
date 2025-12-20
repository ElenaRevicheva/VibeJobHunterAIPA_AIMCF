# 🚀 GO LIVE CHECKLIST - VibeJobHunter

## Your Goal
Make both **ATS submission** and **founder outreach** work together to automatically apply for AI jobs.

---

## ✅ STEP 1: Environment Setup (5 minutes)

Copy `.env.example` to `.env` and fill in:

```bash
cp .env.example .env
```

### Required Variables:
| Variable | Where to get it | Status |
|----------|----------------|--------|
| `ANTHROPIC_API_KEY` | https://console.anthropic.com | ⬜ |
| `RESEND_API_KEY` | https://resend.com/api-keys | ⬜ |
| `RESUME_PATH` | Already set: `autonomous_data/resumes/elena_resume.pdf` | ✅ |

### Optional but Recommended:
| Variable | Purpose | Status |
|----------|---------|--------|
| `HUNTER_API_KEY` | Verify founder emails (reduces bounces) | ⬜ |
| `TELEGRAM_BOT_TOKEN` | Get notifications | ⬜ |

---

## ✅ STEP 2: Test Everything (10 minutes)

Run the test script in dry-run mode:

```bash
python3 scripts/test_job_engine.py
```

Expected output:
- ✅ Environment check PASSED
- ✅ Rate limiter WORKING
- ✅ Email service WORKING
- ✅ Job discovery WORKING
- ✅ Job scoring WORKING
- ✅ ATS submission components READY
- ✅ Founder finder WORKING

**Fix any failures before proceeding!**

---

## ✅ STEP 3: Enable Live Mode

### 3a. Set ATS to Live Mode
In your `.env` file:
```bash
ATS_DRY_RUN=false
```

### 3b. Run ONE Test Application
```bash
python3 scripts/test_job_engine.py --live
```

This will:
1. Find real jobs
2. Score them against your profile
3. Apply to ONE high-match job
4. Send ONE founder email (if applicable)

---

## ✅ STEP 4: Monitor & Adjust

### Check Results:
```bash
# View recent applications
ls -la autonomous_data/applications/

# View email stats
cat autonomous_data/email_stats.json

# View submission log
cat autonomous_data/submissions/submission_log.json
```

### Adjust Thresholds:
In `.env`:
```bash
# Higher = more selective
AUTO_APPLY_THRESHOLD=60

# Lower = more founder outreach
OUTREACH_THRESHOLD=58

# Max applications per day
MAX_DAILY_APPLICATIONS=5
```

---

## ✅ STEP 5: Run Autonomous Mode

Once tests pass, run the full autonomous engine:

```bash
# One cycle (finds jobs, applies, sends outreach)
python3 -m src.main autonomous --interval 1

# Or on Railway (24/7)
railway up
```

---

## 🛡️ SAFETY FEATURES ENABLED

| Feature | Protection |
|---------|------------|
| **Rate Limiting** | Max 10 emails/day, 3/hour |
| **Email Validation** | Blocks careers@, hr@, etc. |
| **Bounce Tracking** | Auto-disables on 3 bounces |
| **Dry Run Default** | ATS submissions are safe by default |
| **Daily Caps** | Max 5 applications/day |

---

## 📊 WHAT HAPPENS WHEN IT'S WORKING

```
🔄 AUTONOMOUS CYCLE COMPLETE

📊 Results:
• 47 jobs found
• 42 jobs scored
• 3 applications sent        ← ATS submissions
• 2 founder outreach sent    ← Direct emails
• 5 saved for review
• 32 jobs discarded

🏆 Top Matches:
1. Anthropic (87/100)
   AI Engineer - Remote
2. Stripe (79/100)
   Founding Engineer - SF/Remote
3. Vercel (75/100)
   Staff Engineer - Remote
```

---

## ❓ TROUBLESHOOTING

### "Rate limited" error
Wait 1 hour or check `autonomous_data/email_stats.json`

### "Email blocked" error
The email is a generic address (careers@). This is correct - use ATS instead.

### "Resume not found"
Set `RESUME_PATH=autonomous_data/resumes/elena_resume.pdf`

### "Playwright error"
Run: `pip install playwright && playwright install chromium`

---

## 🎯 SUCCESS METRICS

After 1 week of running:

| Metric | Target |
|--------|--------|
| Jobs found | 200+ per week |
| Applications sent | 15-25 (quality over quantity) |
| Founder emails sent | 10-15 |
| Response rate | 10-15% |
| Interview requests | 2-5 |

---

**You're ready to go! 🚀**
