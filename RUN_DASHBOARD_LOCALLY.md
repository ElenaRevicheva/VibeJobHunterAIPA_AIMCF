# 🖥️ Run GA4 Dashboard Locally with Railway Credentials

## Quick Method: Create Local .env File

### Step 1: Get Credentials from Railway

1. Go to Railway Dashboard
2. Click your service
3. Click "Variables" tab
4. Copy the VALUES of:
   - `GOOGLE_ANALYTICS_CREDENTIALS`
   - `GA4_PROPERTY_ID`
   - `GA4_MEASUREMENT_ID`

### Step 2: Create .env File Locally

```bash
# In your workspace directory
cat > .env << 'EOF'
# Paste your Railway credentials here
GOOGLE_ANALYTICS_CREDENTIALS={"type":"service_account","project_id":"...","private_key":"..."}
GA4_PROPERTY_ID=123456789
GA4_MEASUREMENT_ID=G-TL5S8V23LT
EOF
```

### Step 3: Run Dashboard

```bash
# Make sure dependencies are installed
pip3 install -r requirements.txt

# View dashboard with REAL data
python3 scripts/view_ga_dashboard.py

# Export report
python3 scripts/view_ga_dashboard.py --export

# View last 30 days
python3 scripts/view_ga_dashboard.py --days 30
```

**Now you'll see REAL data from Google Analytics!** 📊

---

## Alternative: Export Credentials to Shell

```bash
# Set environment variables in current shell
export GOOGLE_ANALYTICS_CREDENTIALS='{"type":"service_account",...}'
export GA4_PROPERTY_ID="123456789"
export GA4_MEASUREMENT_ID="G-TL5S8V23LT"

# Run dashboard
python3 scripts/view_ga_dashboard.py
```

---

## Security Note

⚠️ **Important:**
- Never commit `.env` to git
- Keep credentials secure
- `.env` is already in `.gitignore`
