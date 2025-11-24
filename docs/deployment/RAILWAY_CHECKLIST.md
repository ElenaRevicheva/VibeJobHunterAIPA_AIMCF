# 🔍 Railway Deployment Checklist

**Issue:** LinkedIn CMO code on GitHub but NOT in Railway logs  
**Last Deployment:** 21:02:47 UTC (no LinkedIn CMO messages)  
**Latest Commit:** 305644d + new empty commit  

---

## ✅ Pre-Deployment Checklist (DONE)

- [x] LinkedIn CMO code in git (c726501, 3944c9d)
- [x] Error handling added (6c4eb1c)
- [x] Pushed to origin/main (305644d)
- [x] GitHub confirms code is there
- [x] Forced empty commit to trigger deploy

---

## 🔍 What to Check in Railway Dashboard

### 1. Git Integration (Settings → GitHub)
- [ ] Repo: `ElenaRevicheva/vibejobhunter` ✅?
- [ ] Branch: `main` ✅?
- [ ] Auto-deploy: **ON** ✅?
- [ ] Last sync: Shows recent timestamp?

### 2. Latest Deployment (Deployments Tab)
- [ ] Commit hash: Should be 305644d or newer
- [ ] Build logs: Check which files are copied
- [ ] Deployment status: **Success**?
- [ ] Deployment time: After 21:02 UTC?

### 3. Build Logs (Click deployment → Build Logs tab)
Look for:
```
Cloning repository...
Checking out commit: [SHOULD BE 305644d or newer]
Copying files...
src/notifications/linkedin_cmo.py ← SHOULD BE HERE
```

### 4. Runtime Logs (After deployment)
**Expected:**
```
21:XX:XX | INFO     | 📱 Telegram notifications ENABLED
21:XX:XX | INFO     | 📱 LinkedIn CMO DISABLED  ← THIS LINE
21:XX:XX | INFO     | 🔍 Job Monitor initialized
```

**Or with error:**
```
21:XX:XX | WARNING  | ⚠️ LinkedIn CMO not available: [error]
```

---

## 🚨 If LinkedIn CMO STILL Not in Logs

### Scenario A: Wrong Commit Deployed
**Railway shows old commit in build logs**

**Fix:**
1. Disconnect GitHub integration
2. Reconnect to repo
3. Set branch to `main`
4. Enable auto-deploy
5. Manually trigger redeploy

### Scenario B: File Not Copied During Build
**Build logs don't show linkedin_cmo.py**

**Fix:**
1. Check .dockerignore (shouldn't exclude .py files)
2. Check .gitignore (file should be tracked)
3. Verify file exists: `git ls-tree HEAD:src/notifications/`

### Scenario C: Import Failing Silently
**Correct commit, file exists, but no log message**

**Fix:**
1. SSH into Railway container
2. Check if file exists: `ls /app/src/notifications/linkedin_cmo.py`
3. Try manual import: `python3 -c "from src.notifications import LinkedInCMO"`
4. Check dependencies in Railway environment

---

## 🔧 Railway SSH Debug Commands

If nothing works, SSH into Railway:

```bash
# Connect to Railway shell
railway run bash

# Check file exists
ls -la /app/src/notifications/linkedin_cmo.py

# Check git commit deployed
cat /app/.git/refs/heads/main 2>/dev/null || echo "No .git folder"

# Try import manually
python3 -c "from src.notifications import LinkedInCMO; print('SUCCESS')"

# Check orchestrator code
grep -A 5 "LinkedIn CMO" /app/src/autonomous/orchestrator.py
```

---

## 📊 Expected Timeline

1. **NOW:** Empty commit pushed (forces redeploy)
2. **+2 min:** Railway starts new deployment
3. **+3 min:** Build completes, container restarts
4. **+4 min:** New logs appear with LinkedIn CMO message

**Check Railway logs in 5 minutes!**

---

## ✅ Success Criteria

After new deployment:
- [ ] Railway build logs show commit 305644d+
- [ ] Railway runtime logs show "📱 LinkedIn CMO" message
- [ ] No errors in logs related to import
- [ ] Can add webhook URL to activate LinkedIn CMO

---

**Status:** Waiting for Railway to redeploy with empty commit trigger...
