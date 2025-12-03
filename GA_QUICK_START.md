# 🚀 Google Analytics Quick Start (Super Fast Version)

## TL;DR - 3 Main Steps

### 1️⃣ Create GA4 Account (5 min)
1. Go to https://analytics.google.com
2. Create account → Property → Data Stream
3. Copy your **Measurement ID** (format: `G-XXXXXXXXXX`)

### 2️⃣ Add to Website (2 min)
Add this code to `aideazz.xyz` before `</head>` tag:

```html
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX');
</script>
```

Replace `G-XXXXXXXXXX` with YOUR Measurement ID!

### 3️⃣ Test It Works (1 min)
1. Visit aideazz.xyz
2. Go to GA → Reports → Real-time
3. See yourself in real-time view ✅

---

## 🎯 That's It for Basic Setup!

**For AI Co-Founder to READ the data** (Week 2), you'll need:
- Google Analytics Data API enabled
- Service account created
- Credentials in Railway

But for NOW, just get steps 1-3 done so data starts flowing!

---

## ✅ Quick Verification

Open terminal and test if GA is loaded:

```javascript
// In browser console on aideazz.xyz:
window.dataLayer
// Should show array with data

gtag
// Should show function
```

If both work → ✅ Tracking is active!

---

## 📊 Check Results in 24 Hours

Visit: Google Analytics → Reports → Acquisition → Traffic Acquisition

Filter by: Source contains "linkedin"

You'll see campaigns named: `cmo_post_YYYYMMDD_HHMM`

Each one is a LinkedIn post! Now you know which posts drive traffic! 🎯

---

**Questions?** 
- See full guide: [GOOGLE_ANALYTICS_SETUP.md](./GOOGLE_ANALYTICS_SETUP.md)
- Having issues? Check Troubleshooting section
- Ready for Week 2? Let me know when GA has 24+ hours of data!
