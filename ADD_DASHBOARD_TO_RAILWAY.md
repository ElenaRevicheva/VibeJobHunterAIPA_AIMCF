# 🚂 Add GA4 Dashboard to Railway

There are **3 ways** to access your GA4 dashboard with Railway credentials:

---

## 🎯 Option 1: Run Locally with Railway Credentials (EASIEST)

**Best for:** Quick checks, development, exporting reports

### Steps:

1. **Get credentials from Railway:**
   - Railway Dashboard → Your Service → Variables tab
   - Copy values of: `GOOGLE_ANALYTICS_CREDENTIALS`, `GA4_PROPERTY_ID`, `GA4_MEASUREMENT_ID`

2. **Create local `.env` file:**
   ```bash
   cat > .env << 'EOF'
   GOOGLE_ANALYTICS_CREDENTIALS={"type":"service_account",...paste from Railway...}
   GA4_PROPERTY_ID=123456789
   GA4_MEASUREMENT_ID=G-TL5S8V23LT
   EOF
   ```

3. **Run dashboard:**
   ```bash
   python3 scripts/view_ga_dashboard.py
   ```

**✅ Now shows REAL data from Google Analytics!**

See: `RUN_DASHBOARD_LOCALLY.md` for details

---

## 🌐 Option 2: Add Web Dashboard to Railway (BEST FOR PRODUCTION)

**Best for:** Always-on dashboard, share with team, bookmarkable URL

### Step 1: Add Routes to FastAPI App

In your `src/api/app.py` file, add:

```python
from src.api.ga_dashboard_routes import router as analytics_router

# Add to your FastAPI app
app.include_router(analytics_router)
```

### Step 2: Update app.py

```python
# src/api/app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import the new router
from src.api.ga_dashboard_routes import router as analytics_router

app = FastAPI(
    title="VibeJobHunter API",
    description="AI-powered job hunting automation with GA4 analytics",
    version="4.0.0"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include analytics router
app.include_router(analytics_router)

# Your existing routes...
@app.get("/")
async def root():
    return {"message": "VibeJobHunter API with GA4 Analytics"}

# ... rest of your app
```

### Step 3: Deploy to Railway

```bash
git add src/api/ga_dashboard_routes.py src/api/app.py
git commit -m "Add GA4 dashboard web interface"
git push
```

### Step 4: Access Your Dashboard!

After deployment completes:

**URLs:**
- **Dashboard:** `https://your-app.railway.app/analytics/dashboard`
- **JSON API:** `https://your-app.railway.app/analytics/metrics`
- **Health Check:** `https://your-app.railway.app/analytics/health`
- **Last 30 days:** `https://your-app.railway.app/analytics/dashboard?days=30`

**Bookmark it!** 📌

---

## 💻 Option 3: Use Railway CLI

**Best for:** Running commands directly on Railway

### Install Railway CLI:

```bash
npm install -g @railway/cli

# Or with Homebrew
brew install railway
```

### Login and Link:

```bash
railway login
railway link
```

### Run Dashboard Commands:

```bash
# Run dashboard on Railway
railway run python3 scripts/view_ga_dashboard.py

# Export report
railway run python3 scripts/view_ga_dashboard.py --export

# Run any Python command with Railway env vars
railway run python3 -c "from src.dashboard.performance_tracker import GA4PerformanceTracker; t=GA4PerformanceTracker(); print(t.get_website_metrics(7))"
```

---

## 📊 Comparison

| Method | Pros | Cons | Best For |
|--------|------|------|----------|
| **Local with .env** | Fast, flexible, easy | Need to copy credentials | Quick checks, development |
| **Web Dashboard** | Always available, shareable, no setup | Need to redeploy code | Production, team access |
| **Railway CLI** | Direct access, no code changes | Need CLI installed | Ad-hoc queries |

---

## 🎯 Recommended Setup

**For most users:**

1. **Week 1:** Use **Option 1** (local with .env) for quick testing
2. **Week 2:** Add **Option 2** (web dashboard) for permanent access
3. **Optional:** Install Railway CLI for occasional direct access

---

## 🚀 Quick Start: Option 2 (Web Dashboard)

**In 5 minutes:**

1. Copy `src/api/ga_dashboard_routes.py` (already created ✅)

2. Update `src/api/app.py`:
   ```python
   from src.api.ga_dashboard_routes import router as analytics_router
   app.include_router(analytics_router)
   ```

3. Commit and push:
   ```bash
   git add .
   git commit -m "Add GA4 web dashboard"
   git push
   ```

4. Wait for Railway deployment (~2 min)

5. Visit: `https://your-app.railway.app/analytics/dashboard`

**Done!** 🎉

---

## 📱 What You'll See

**Web Dashboard includes:**
- 📊 Key metrics (users, sessions, pageviews)
- 📈 Engagement stats (bounce rate, duration)
- 🔝 Top performing pages
- 🌐 Traffic sources (including LinkedIn!)
- 🔄 Refresh button
- 📅 7/30 day views
- 💾 JSON export

**Screenshot:**
```
┌─────────────────────────────────────────────┐
│  📊 AIdeazz.xyz Performance Dashboard       │
│  Last 7 days • Updated: 2025-12-04 16:30    │
│  [🔄 Refresh] [7 Days] [30 Days] [JSON API] │
└─────────────────────────────────────────────┘

┌──────────┬──────────┬──────────┬──────────┐
│ Users    │ Sessions │ Pageviews│ Duration │
│  1,234   │  2,456   │  5,678   │  145s    │
└──────────┴──────────┴──────────┴──────────┘

🔝 Top Pages
─────────────────────────────────────────────
• Home Page - 2,345 views
• About - 1,234 views

🌐 Traffic Sources
─────────────────────────────────────────────
• linkedin / social - 1,234 sessions ← Your posts!
• google / organic - 789 sessions
```

---

## 🔧 Troubleshooting

### "Dashboard shows zeros"
- Wait 24-48 hours after setup
- Check GA Real-time view has activity
- Verify website has tracking code

### "Can't access /analytics/dashboard"
- Make sure you deployed the new code
- Check Railway logs for errors
- Verify FastAPI app includes the router

### "Health check shows 'degraded'"
- Check Railway environment variables
- Verify GOOGLE_ANALYTICS_CREDENTIALS is set
- Redeploy Railway

---

## 💡 Pro Tips

1. **Bookmark dashboard URL** - Quick access anytime
2. **Check daily** - Monitor data flow
3. **Use JSON API** - Integrate with other tools
4. **Share URL** - Show team your metrics
5. **Try different periods** - ?days=7 vs ?days=30

---

**Choose Option 2 for best experience! Takes 5 minutes, works forever.** 🚀
