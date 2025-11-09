# 🚀 VibeJobHunter

**Maximum Automation AI Agent for Job Hunting**

Find jobs on LinkedIn → AI generates everything → You click Submit  
**10 applications in 15 minutes!**

---

## ⚡ **Quick Start** (5 minutes)

### **1. Setup**

```powershell
# Windows - just double-click:
vibe.bat

# OR manually:
python -m pip install anthropic click rich fastapi uvicorn aiohttp beautifulsoup4 pypdf2 pydantic pydantic-settings python-dotenv requests
```

### **2. Find Jobs**

Open LinkedIn/Indeed, find 5-10 jobs, copy URLs

### **3. Create jobs.txt**

```
notepad jobs.txt
```

Paste URLs (one per line):
```
https://www.linkedin.com/jobs/view/123456/
https://www.linkedin.com/jobs/view/789012/
```

### **4. Run!**

```powershell
python -m src.main batch --file jobs.txt
```

**AI does everything. You just click Submit!**

---

## 🎯 **Two Modes:**

### **Mode 1: BATCH APPLY** ⭐ (Recommended)

**Best for: Maximum success rate**

1. You find 10 jobs on LinkedIn
2. Copy URLs to jobs.txt
3. Run batch command
4. AI generates everything
5. You submit in 30 sec each

**= 10 applications in 15 minutes**

### **Mode 2: AUTOPILOT**

**Best for: Maximum laziness**

1. AI searches for jobs
2. AI scores them
3. AI generates materials
4. Opens tabs for you

**= Less reliable (scrapers get blocked)**

---

## ✨ **What AI Does:**

✅ Analyzes job descriptions  
✅ Calculates match score (0-100)  
✅ Tailors your resume to each job  
✅ Writes personalized cover letters  
✅ Tracks all applications  
✅ Reminds you about follow-ups  

---

## 📊 **Results:**

```
15 min/day × 20 days = 200 applications/month
200 apps × 10% response = 20 interviews  
20 interviews × 30% success = 6 offers

YOU CHOOSE YOUR NEXT ROLE! 🎉
```

---

## 📖 **Full Documentation:**

- **BATCH_APPLY_GUIDE.md** - Complete batch apply guide
- **START_HERE_IMPROVED.md** - Detailed quick start  
- **WINDOWS_SETUP.md** - Windows setup help
- **VIBE_MODE.md** - Philosophy & approach

---

**AI-Powered Job Hunting Agent** - Automatically find, match, and apply to your dream jobs.

Built for Elena Revicheva's job search, but designed to help any AI engineer, developer, or startup builder land their next role **fast**.

---

## ✨ Features

### 🤖 AI-Powered Automation
- **Smart Job Search**: Scrapes LinkedIn, Indeed, and other platforms for relevant positions
- **Intelligent Matching**: Uses Claude AI to score jobs based on your profile (0-100 match score)
- **Auto-Tailoring**: Generates customized resumes and cover letters for each application
- **Application Tracking**: Monitors all applications with status updates and follow-up reminders
- **Interview Prep**: Creates company research, likely questions, and talking points

### 🎯 Key Capabilities
- Searches multiple job platforms simultaneously
- Filters by skills, location, remote preference, salary
- Ranks jobs by relevance to your background
- Generates personalized application materials
- Tracks application pipeline (applied → interviewing → offer)
- Schedules follow-ups automatically
- Beautiful web dashboard for monitoring progress

### 📊 Analytics
- Daily/weekly application metrics
- Response rate tracking
- Match score analytics
- Follow-up reminders
- Application status breakdown

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Anthropic API key (for Claude AI)
- Your resume in PDF format

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd vibejobhunter

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your API keys
```

### Configuration

Edit `.env` file:
```bash
# Required
ANTHROPIC_API_KEY=your_anthropic_key_here

# Optional (for enhanced features)
OPENAI_API_KEY=your_openai_key
LINKEDIN_EMAIL=your_email
LINKEDIN_PASSWORD=your_password
```

---

## 📝 Usage

### 1. Setup Your Profile

```bash
python -m src.main setup --resume "Elena Revicheva 03.11.2025 Resume.pdf"
```

This will:
- Extract text from your resume
- Use AI to parse your experience, skills, and achievements
- Create your job-hunting profile
- Save to `data/profiles/profile.json`

### 2. Search for Jobs

```bash
# Search with default settings (from config)
python -m src.main search

# Custom search
python -m src.main search \
  --keywords "AI Engineer" "Founding Engineer" \
  --location "Remote" \
  --remote \
  --limit 100 \
  --min-score 70
```

This will:
- Search LinkedIn and Indeed for matching jobs
- Score each job against your profile
- Filter by minimum match score
- Save jobs to `data/jobs/`

### 3. Apply to Jobs

```bash
# Apply to top 5 matches
python -m src.main apply --top 5

# Auto-mode (no confirmations)
python -m src.main apply --top 10 --auto
```

This will:
- Select top unapplied jobs by match score
- Generate tailored resume for each job
- Write custom cover letter
- Save materials to `tailored_resumes/` and `cover_letters/`
- Track applications in `data/applications/`

**Note**: Currently requires manual submission to job sites. Auto-submission coming soon!

### 4. Check Status

```bash
# View all statistics
python -m src.main status

# Check follow-ups needed
python -m src.main followup
```

### 5. Launch Dashboard

```bash
# Start web dashboard
python -m src.main dashboard --port 8000
```

Then open http://localhost:8000 in your browser.

---

## 📁 Project Structure

```
vibejobhunter/
├── src/
│   ├── core/              # Core functionality
│   │   ├── config.py      # Configuration management
│   │   ├── models.py      # Data models
│   │   └── profile_manager.py  # Profile handling
│   ├── agents/            # AI agents
│   │   ├── job_matcher.py       # Job matching logic
│   │   ├── content_generator.py # Resume/cover letter generation
│   │   └── application_manager.py # Application tracking
│   ├── scrapers/          # Job scrapers
│   │   ├── linkedin_scraper.py
│   │   └── indeed_scraper.py
│   ├── api/               # Web API & dashboard
│   │   └── app.py
│   └── main.py            # CLI entry point
├── data/                  # Data storage
│   ├── profiles/          # User profiles
│   ├── jobs/              # Discovered jobs
│   ├── applications/      # Application tracking
│   └── stats/             # Analytics
├── tailored_resumes/      # Generated resumes
├── cover_letters/         # Generated cover letters
├── templates/             # Email/message templates
└── logs/                  # Application logs
```

---

## 🎯 How It Works

### 1. Profile Creation
- Parses your resume using Claude AI
- Extracts skills, experience, achievements
- Identifies target roles and preferences

### 2. Job Discovery
- Searches multiple platforms simultaneously
- Applies filters (location, remote, keywords)
- Extracts job details, requirements, descriptions

### 3. Intelligent Matching
- Scores each job 0-100 based on:
  - Skill alignment
  - Experience level fit
  - Location/remote compatibility
  - Role type match
  - Growth potential
- Provides specific match reasons

### 4. Content Generation
- **Tailored Resume**: Emphasizes relevant achievements, reorders skills
- **Cover Letter**: Personalized to company/role with specific examples
- **LinkedIn Messages**: Brief, professional outreach templates

### 5. Application Tracking
- Tracks status: Found → Reviewed → Applied → Interviewing → Offer
- Schedules follow-ups (default: 7 days)
- Monitors response rates
- Generates interview prep materials

---

## 🔧 Advanced Configuration

### Target Roles
Edit `src/core/config.py` to customize:

```python
target_roles = [
    "AI Engineer",
    "Founding Engineer",
    "Full-Stack AI Engineer",
    "LLM Engineer",
    # Add your roles...
]

target_keywords = [
    "AI", "Machine Learning", "LLM",
    "Python", "TypeScript", "React",
    # Add your keywords...
]

excluded_keywords = [
    "PhD required",
    "10+ years required",
    # Add exclusions...
]
```

### Application Limits

```python
MAX_DAILY_APPLICATIONS=20  # Daily limit
AUTO_APPLY_ENABLED=false   # Manual review mode
```

---

## 📊 API Endpoints

The dashboard exposes these endpoints:

- `GET /api/stats` - Overall statistics
- `GET /api/profile` - Your profile
- `GET /api/jobs` - All discovered jobs
- `GET /api/jobs/top?limit=10` - Top unapplied matches
- `GET /api/applications` - All applications
- `GET /api/applications?status=interviewing` - Filter by status
- `GET /api/followups` - Applications needing follow-up

Full API docs at: http://localhost:8000/docs

---

## 🤝 Contributing

This project was built for Elena's job search, but feel free to:
- Fork for your own use
- Submit PRs for improvements
- Report issues
- Share success stories!

---

## 📄 License

MIT License - Use freely!

---

## 🌟 Success Story

This tool was built by Elena Revicheva, who:
- Built 6 AI products solo in 7 months
- Achieved 98% cost reduction vs team-based development
- Serves users in 19 Spanish-speaking countries
- Integrated 8+ AI services (Claude, GPT, Whisper, ElizaOS, etc.)

Now she's using AI to help AI find her next AI role. Meta! 🤯

---

## 💡 Tips for Best Results

1. **Update your profile regularly** - Keep skills and achievements current
2. **Set realistic match score thresholds** - 60-70 is a good starting point
3. **Review generated content** - AI is great but always proofread
4. **Track everything** - Follow-ups matter!
5. **Customize for each role** - Even AI-generated content benefits from personal touches
6. **Network in parallel** - Don't rely solely on applications
7. **Stay consistent** - Apply to 5-10 quality jobs daily

---

## 🆘 Troubleshooting

### "No profile found"
Run `python -m src.main setup` first

### Scraper errors
- LinkedIn/Indeed may block automated requests
- Use VPN or proxy if needed
- Rate limit: 50 jobs per search recommended

### API key errors
- Check `.env` file exists and has valid keys
- Ensure `ANTHROPIC_API_KEY` is set

### Dashboard won't start
```bash
pip install fastapi uvicorn
python -m src.main dashboard
```

---

## 🚀 Roadmap

- [ ] Auto-submission to easy-apply jobs
- [ ] Email application automation
- [ ] AngelList integration
- [ ] Y Combinator jobs scraper
- [ ] Twitter/X job monitoring
- [ ] Slack/Discord notifications
- [ ] LinkedIn auto-networking
- [ ] Interview scheduler integration
- [ ] Salary negotiation assistant
- [ ] Multi-language support

---

## 📞 Contact

Built with ❤️ by Elena Revicheva

- 🌐 Website: [aideazz.xyz](https://aideazz.xyz)
- 💼 LinkedIn: [LinkedIn Profile](https://linkedin.com/in/yourprofile)
- 🐦 Twitter: [@yourusername](https://twitter.com/yourusername)
- 📧 Email: your@email.com

---

**Happy job hunting! May your vibe attract your tribe.** ✨🚀
