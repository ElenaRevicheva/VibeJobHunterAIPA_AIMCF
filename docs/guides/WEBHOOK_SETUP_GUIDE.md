# 🚀 LinkedIn CMO Webhook Setup Guide

## ✅ Current Status

**LinkedIn CMO is DEPLOYED to Railway!** 🎉

- ✅ Code merged to `main` branch
- ✅ Railway auto-deployed (commit: c726501)
- ✅ LinkedIn CMO integrated into autonomous orchestrator
- ⏳ **Waiting for Make.com webhook URL** (won't post until you add it)

## 📋 Quick Setup (3 Options)

### Option A: Add Webhook via Railway Dashboard (EASIEST) ⭐

**This is the recommended approach!**

1. Go to [Railway Dashboard](https://railway.app/)
2. Select your VibeJobHunter project
3. Click **"Variables"** tab
4. Click **"+ New Variable"**
5. Add:
   ```
   MAKE_WEBHOOK_URL_LINKEDIN=https://hook.us2.make.com/YOUR_WEBHOOK_HERE
   ```
6. Click **"Deploy"** (Railway will restart with new variable)

**Done!** LinkedIn CMO will start posting Mon/Wed/Fri at 10 AM. 🎯

---

### Option B: Add Webhook via Local .env (FOR LOCAL TESTING)

If you want to test locally first:

```bash
# Create .env file (if not exists)
cp .env.example .env

# Edit .env file
nano .env  # or use your favorite editor

# Add this line:
MAKE_WEBHOOK_URL_LINKEDIN=https://hook.us2.make.com/YOUR_WEBHOOK_HERE
```

Then test locally:
```bash
# Test post generation
python -c "from src.notifications.linkedin_cmo import LinkedInCMO; cmo = LinkedInCMO(); print(cmo.generate_linkedin_post('open_to_work', 'en')['content'])"

# Test full posting flow (requires webhook)
python -c "import asyncio; from src.notifications.linkedin_cmo import LinkedInCMO; cmo = LinkedInCMO(); asyncio.run(cmo.post_to_linkedin('technical_showcase', 'en'))"
```

---

### Option C: Commit .env to Git (NOT RECOMMENDED)

**⚠️ WARNING:** This exposes your webhook URL in git history!

Only do this if:
- Your repo is private
- You're okay with webhook URL in git history
- You need persistent config across deployments

```bash
# Edit .env
nano .env

# Add webhook URL
MAKE_WEBHOOK_URL_LINKEDIN=https://hook.us2.make.com/YOUR_WEBHOOK_HERE

# Commit (BE CAREFUL!)
git add .env
git commit -m "Add Make.com webhook for LinkedIn CMO"
git push origin main
```

---

## 📱 How LinkedIn CMO Works

### Posting Schedule
- **Monday**: English post (10 AM)
- **Wednesday**: Spanish post (10 AM)
- **Friday**: English post (10 AM)

### Content Types (Random Selection)
**English:**
- `open_to_work` - Job hunting post
- `technical_showcase` - Engineering deep-dive
- `transformation_story` - Your journey from executive to engineer
- `seeking_funding` - AIdeazz fundraising pitch

**Spanish:**
- `busco_trabajo` - Job hunting post (ES)
- `historia_transformacion` - Transformation story (ES)

### Architecture
```
LinkedIn CMO → Make.com Webhook → Buffer → LinkedIn
```

### Safety Features
✅ **Won't post without webhook URL** (safe to deploy)
✅ **Logs clearly** when disabled vs. enabled
✅ **Separate from job search** notifications (uses Telegram)
✅ **Bilingual** content (EN/ES) based on Elena's resume

---

## 🔧 Testing Locally

### 1. Test Content Generation (No Webhook Needed)
```bash
python -c "from src.notifications.linkedin_cmo import LinkedInCMO; cmo = LinkedInCMO(); post = cmo.generate_linkedin_post('transformation_story', 'en'); print(post['content'])"
```

### 2. Test Full Posting Flow (Requires Webhook)
```bash
# Set webhook URL first
export MAKE_WEBHOOK_URL_LINKEDIN="https://hook.us2.make.com/YOUR_WEBHOOK_HERE"

# Test posting
python -c "import asyncio; from src.notifications.linkedin_cmo import LinkedInCMO; cmo = LinkedInCMO(); asyncio.run(cmo.post_to_linkedin('open_to_work', 'en'))"
```

### 3. Check Logs
```bash
# LinkedIn CMO logs show:
# - "📱 LinkedIn CMO ENABLED (via Make.com)" - Webhook is set ✅
# - "📱 LinkedIn CMO DISABLED (set MAKE_WEBHOOK_URL_LINKEDIN to enable)" - No webhook ⚠️
```

---

## 🎯 Make.com Webhook Setup

### 1. Create Make.com Scenario

1. Go to [Make.com](https://www.make.com/)
2. Create new scenario: **"LinkedIn CMO → Buffer"**
3. Add modules:
   - **Webhooks** → "Custom webhook"
   - **Buffer** → "Create a new update"
   - **LinkedIn** (via Buffer profile)

### 2. Configure Webhook Module

- Click webhook → **"Copy address to clipboard"**
- This is your `MAKE_WEBHOOK_URL_LINKEDIN`
- Paste it into Railway dashboard (Option A above)

### 3. Map Webhook Data to Buffer

In Buffer module, map:
- `content` → Buffer "Text" field
- `language` → Buffer "Profile" (EN vs ES LinkedIn accounts if you have 2)
- `post_type` → Add as tag or note
- `timestamp` → For scheduling

### 4. Test the Flow

Run test command (Option B above) and check:
- ✅ Make.com receives webhook
- ✅ Buffer queues post
- ✅ LinkedIn post appears

---

## 🚨 Troubleshooting

### "LinkedIn CMO DISABLED" in Logs
**Solution:** Add webhook URL to Railway dashboard (Option A)

### "Make.com webhook failed: 404"
**Solution:** Check webhook URL is correct (no typos)

### Posts Not Appearing on LinkedIn
**Check:**
1. Is it Mon/Wed/Fri at 10 AM? (LinkedIn CMO only posts on schedule)
2. Is Make.com scenario active?
3. Is Buffer connected to LinkedIn?
4. Check Railway logs: `railway logs --tail 100`

### Want to Post Immediately (Skip Schedule)
**Run manually:**
```python
# In Railway shell or locally
import asyncio
from src.notifications.linkedin_cmo import LinkedInCMO

cmo = LinkedInCMO()
asyncio.run(cmo.post_to_linkedin('open_to_work', 'en'))
```

---

## 📊 Expected Behavior After Setup

### Immediately After Adding Webhook
- ✅ LinkedIn CMO shows "ENABLED" in logs
- ⏳ Won't post until next scheduled time (Mon/Wed/Fri 10 AM)

### On Monday/Wednesday/Friday at 10 AM
- 📝 Generates random post (EN on Mon/Fri, ES on Wed)
- 📤 Sends to Make.com webhook
- ✅ Logs: "🎉 LinkedIn post sent successfully!"

### In Make.com Dashboard
- ✅ Webhook received (see operations history)
- ✅ Buffer queued post
- ✅ LinkedIn post scheduled/published

---

## 🎉 Next Steps

1. **Get Make.com webhook URL** (create scenario)
2. **Add to Railway dashboard** (Option A - EASIEST)
3. **Wait for next Mon/Wed/Fri at 10 AM** OR test manually
4. **Monitor logs** to confirm posting
5. **Check LinkedIn** to see your posts! 🚀

---

## 📝 Notes

- **Railway handles env vars automatically** (no .env file needed in production)
- **LinkedIn CMO is SEPARATE from job search notifications** (Telegram)
- **Bilingual content is pre-written** (no Claude API needed for posting)
- **Make.com is the middle layer** (handles Buffer → LinkedIn posting)

---

**Need help?** Check Railway logs or test locally first! 🔥
