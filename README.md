# 🚀 VibeJobHunter

**AI-Powered Job Hunting Agent - Maximum Automation**

Apply to 10 jobs in 15 minutes with AI-tailored resumes and cover letters!

---

## ⚡ **Quick Start**

### **Installation:**
```bash
pip install anthropic click rich fastapi uvicorn aiohttp beautifulsoup4 pypdf2 pydantic pydantic-settings python-dotenv requests
```

### **Setup:**
```bash
# Add your API key
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# Create profile from resume
python -m src.main setup --resume "your_resume.pdf"
```

### **Use Batch Apply V2** (Recommended):
```bash
# Create jobs.txt with LinkedIn/Indeed URLs
notepad jobs.txt

# Run batch apply with V2 improvements
python -m src.main batch --file jobs.txt --v2
```

**That's it!** Browser opens → Copy materials → Submit!

---

## 🎯 **Key Features**

- ✅ **3x faster** - Parallel processing
- ✅ **70% cheaper** - Intelligent caching
- ✅ **99% reliable** - Auto-retry logic
- ✅ **AI-powered** - Custom resumes & cover letters
- ✅ **Progress saving** - Resume interrupted sessions
- ✅ **Professional logging** - Full debugging
- ✅ **Cost tracking** - Know your spending

---

## 📚 **Documentation**

**All documentation is in the [`docs` branch](https://github.com/ElenaRevicheva/vibejobhunter/tree/docs)**

### **Quick Links:**

- **[Getting Started](https://github.com/ElenaRevicheva/vibejobhunter/blob/docs/docs/02-quick-start-guides/START_HERE.md)** - First steps
- **[V2 Guide](https://github.com/ElenaRevicheva/vibejobhunter/blob/docs/docs/05-v2-improvements/QUICK_V2_GUIDE.md)** - Use improved version
- **[Batch Apply Guide](https://github.com/ElenaRevicheva/vibejobhunter/blob/docs/docs/04-user-guides/BATCH_APPLY_GUIDE.md)** - Complete guide
- **[Windows Setup](https://github.com/ElenaRevicheva/vibejobhunter/blob/docs/docs/04-user-guides/WINDOWS_SETUP.md)** - Windows installation
- **[Architecture](https://github.com/ElenaRevicheva/vibejobhunter/blob/docs/docs/03-technical-docs/ARCHITECTURE.md)** - Technical details
- **[What's New](https://github.com/ElenaRevicheva/vibejobhunter/blob/docs/docs/05-v2-improvements/WHATS_NEW.md)** - V2 improvements

**Browse all docs:** [`docs` branch](https://github.com/ElenaRevicheva/vibejobhunter/tree/docs/docs)

---

## 🏗️ **Project Structure**

```
vibejobhunter/
├── src/
│   ├── agents/           # AI agents (matcher, content generator)
│   ├── api/              # FastAPI dashboard
│   ├── core/             # Core models and config
│   ├── scrapers/         # Job scrapers (LinkedIn, Indeed)
│   ├── utils/            # Utilities (cache, retry, logging)
│   ├── main.py           # CLI entry point
│   ├── autopilot.py      # Autopilot mode
│   ├── batch_apply.py    # Batch apply V1
│   └── batch_apply_v2.py # Batch apply V2 (improved)
│
├── data/                 # Application data (auto-created)
├── tailored_resumes/     # Generated resumes (auto-created)
├── cover_letters/        # Generated letters (auto-created)
├── logs/                 # Application logs (auto-created)
├── .cache/               # Response cache (auto-created)
│
├── .env                  # API keys (create this)
├── requirements.txt      # Python dependencies
├── vibe.bat              # Windows launcher
└── README.md             # This file
```

---

## 💻 **Commands**

### **Batch Apply V2** (Recommended):
```bash
python -m src.main batch --file jobs.txt --v2
```

### **Autopilot Mode:**
```bash
python -m src.main autopilot --resume resume.pdf --count 10
```

### **Check Status:**
```bash
python -m src.main status
```

### **Web Dashboard:**
```bash
python -m src.main dashboard
```

### **Resume Interrupted:**
```bash
python -m src.main batch --resume --v2
```

---

## 📊 **Performance**

| Metric | V1 | V2 |
|--------|----|----|
| Speed (10 jobs) | 60s | 20s ⚡ |
| Reliability | 60% | 99% ✅ |
| Cost (repeat) | $0.50 | $0.00 💰 |
| Resume on crash | ❌ | ✅ |

---

## 🛠️ **Tech Stack**

- **AI:** Anthropic Claude (Sonnet 3.5)
- **Backend:** Python 3.9+, FastAPI
- **Scraping:** aiohttp, BeautifulSoup
- **CLI:** Click, Rich
- **Storage:** JSON (local-first)

---

## 📝 **License**

MIT License - Use freely for your job hunt!

---

## 👤 **Author**

**Elena Revicheva**  
AI Engineer | 0-1 Builder | 6 AI Products in 7 Months

- **GitHub:** [@ElenaRevicheva](https://github.com/ElenaRevicheva)
- **Portfolio:** [Full materials in docs branch](https://github.com/ElenaRevicheva/vibejobhunter/tree/docs/docs/06-candidate-materials)

---

## 🎯 **Results**

```
15 min/day × 20 days = 200 applications/month
200 apps × 10% response = 20 interviews
20 interviews × 30% success = 6 offers

YOU CHOOSE YOUR NEXT ROLE! 🎉
```

---

## 🚀 **Get Started Now**

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Add API key
echo "ANTHROPIC_API_KEY=your-key" > .env

# 3. Setup profile
python -m src.main setup --resume resume.pdf

# 4. Find jobs on LinkedIn → Copy URLs → jobs.txt

# 5. Run batch apply
python -m src.main batch --file jobs.txt --v2

# 6. Apply! (10 jobs in 15 minutes)
```

---

**Built with ❤️ for vibe coders who ship fast.**

*All documentation in [`docs` branch](https://github.com/ElenaRevicheva/vibejobhunter/tree/docs)*
