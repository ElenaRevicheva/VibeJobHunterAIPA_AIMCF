# 🧪 Test GA4 Integration Locally First

Before waiting for Railway, let's test everything works on your local machine!

---

## Quick Local Test (5 minutes)

### Step 1: Create local .env file

```bash
# In your workspace directory
cat > .env << 'EOF'
# Paste your credentials from Railway here

# From Railway Variables tab, copy the VALUE of each:
GOOGLE_ANALYTICS_CREDENTIALS={"type":"service_account","project_id":"...","private_key":"..."}
GA4_PROPERTY_ID=123456789
GA4_MEASUREMENT_ID=G-XXXXXXXXXX
EOF
```

**💡 Tip:** Copy values directly from Railway dashboard

---

### Step 2: Install dependencies

```bash
# Make sure you have Python 3
python3 --version

# Install requirements
pip3 install -r requirements.txt

# Or install just what you need
pip3 install google-analytics-data google-auth rich python-dotenv
```

---

### Step 3: Run the test script

```bash
python3 scripts/test_ga_tracker.py
```

**✅ Expected Output (Success):**
```
🧪 Google Analytics 4 Setup Test
Testing your GA4 configuration...

Step 1: Checking Environment Variables
  ✅ GOOGLE_ANALYTICS_CREDENTIALS is set
  ✅ GA4_PROPERTY_ID is set: 123456789
  ✅ GA4_MEASUREMENT_ID is set: G-XXXXXXXXXX

Step 2: Initializing GA4 Performance Tracker
  ✅ Tracker initialized successfully
  ✅ GA4 API client connected

Step 3: Testing Data Fetch
  ✅ Successfully fetched GA4 data
     Users: 0
     Sessions: 0
     Pageviews: 0

✅ SUCCESS!
Your Google Analytics 4 setup is working correctly!
```

**📝 Note:** Zeros are normal if you haven't added tracking to website yet!

---

### Step 4: View the dashboard

```bash
python3 scripts/view_ga_dashboard.py
```

You should see a beautiful dashboard with metrics (currently zeros if no tracking yet).

---

## ❌ Common Errors & Fixes

### Error: "ModuleNotFoundError: No module named 'google'"

**Fix:**
```bash
pip3 install google-analytics-data google-auth
```

### Error: "ModuleNotFoundError: No module named 'rich'"

**Fix:**
```bash
pip3 install rich
```

### Error: "GOOGLE_ANALYTICS_CREDENTIALS not set"

**Fix:**
```bash
# Make sure .env file exists
ls -la .env

# Check contents (will show your credentials)
cat .env

# Load environment variables
export $(cat .env | xargs)

# Try again
python3 scripts/test_ga_tracker.py
```

### Error: "Invalid credentials" or "Permission denied"

**Fix:**
1. Verify service account has access to GA property:
   - Go to Google Analytics
   - Admin → Property Access Management
   - Your service account email should be listed
   - Role should be "Viewer" or higher

2. Check JSON is valid:
   - Copy GOOGLE_ANALYTICS_CREDENTIALS value
   - Paste into https://jsonlint.com
   - Should validate without errors

3. Try re-downloading credentials:
   - Go to Google Cloud Console
   - APIs & Services → Credentials
   - Find your service account
   - Create new key (JSON)
   - Use new credentials

---

## ✅ If Local Test Works

**Great! Now you know:**
- ✅ Credentials are valid
- ✅ Code works correctly
- ✅ API connection successful

**Railway should work too!** Just need to:
1. Verify Railway variables match your local .env
2. Redeploy Railway
3. Check Railway logs for "GA4 client ready"

---

## 📝 Next Steps After Local Success

### 1. Add tracking to aideazz.xyz

See `GA_TRACKING_CODE.html` for the code to add.

### 2. Verify tracking in browser

```
1. Visit aideazz.xyz
2. Press F12 (DevTools)
3. Network tab
4. Look for google-analytics.com requests
```

### 3. Check Google Analytics Real-time

```
1. Go to analytics.google.com
2. Reports → Real-time
3. Should see yourself online!
```

### 4. Wait 24-48 hours

After tracking is live, GA needs time to collect meaningful data.

### 5. Run dashboard again

```bash
python3 scripts/view_ga_dashboard.py
```

Now you'll see REAL numbers! 🎉

---

## 🚀 Quick Commands

```bash
# Test setup
python3 scripts/test_ga_tracker.py

# View dashboard
python3 scripts/view_ga_dashboard.py

# View last 30 days
python3 scripts/view_ga_dashboard.py --days 30

# Export report
python3 scripts/view_ga_dashboard.py --export

# Test in Python
python3 -c "
from src.dashboard.performance_tracker import GA4PerformanceTracker
tracker = GA4PerformanceTracker()
print('Client connected:', tracker.client is not None)
metrics = tracker.get_website_metrics(days=7)
print(f'Users: {metrics[\"users\"]}')
"
```

---

## 💡 Understanding the Output

### If you see zeros (Users: 0, Sessions: 0):

**This is NORMAL if:**
- ✅ Just set up (< 24 hours of data)
- ✅ Tracking code not on website yet
- ✅ Website has no visitors yet

**The important part is:**
- ✅ "GA4 API client connected" 
- ✅ "Successfully fetched GA4 data"

This means credentials work and will show data once available!

### If you see actual numbers:

**🎉 AWESOME!** Your GA4 is already collecting data!

This means:
- ✅ Tracking code is on website
- ✅ Visitors have come to site
- ✅ Data is flowing to GA
- ✅ API is reading it correctly
- ✅ Everything works perfectly!

---

## 🎯 Success Criteria

**Local test passes when you see:**
1. ✅ All environment variables loaded
2. ✅ Tracker initialized successfully
3. ✅ GA4 API client connected
4. ✅ Data fetched (even if zeros)
5. ✅ Dashboard displays without errors

**Then Railway will work too!**

---

## 🔄 Compare Local vs Railway

| Aspect | Local | Railway |
|--------|-------|---------|
| Credentials | .env file | Railway Variables |
| Python | Your machine | Railway container |
| Testing | Immediate | After redeploy |
| Debugging | Easy (see errors) | Check logs |

**💡 Pro Tip:** Always test locally first! Faster debugging.

---

**Ready?** Let's test!

```bash
python3 scripts/test_ga_tracker.py
```
