# 🎯 Getting Started with VibeJobHunter

**Complete beginner's guide to landing your dream job with AI automation.**

---

## 🎬 What is VibeJobHunter?

VibeJobHunter is an AI-powered job hunting agent that:
- **Searches** multiple job platforms for you
- **Scores** each job based on your profile (0-100)
- **Generates** tailored resumes and cover letters
- **Tracks** all your applications
- **Reminds** you to follow up
- **Analyzes** your job search metrics

Think of it as your personal AI recruiting assistant, working 24/7 to help you land interviews.

---

## 🚀 Installation (5 minutes)

### Step 1: Get the Code

```bash
# If you have the code
cd vibejobhunter

# Or clone from git
git clone <your-repo-url>
cd vibejobhunter
```

### Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

**Requirements:**
- Python 3.9 or higher
- pip (Python package manager)

### Step 3: Get Your API Key

1. Go to https://console.anthropic.com/
2. Sign up for an account (free tier available)
3. Generate an API key
4. Copy the key (starts with `sk-ant-`)

### Step 4: Configure

```bash
# Run the setup script
python setup.py
```

This will:
- Create your `.env` file
- Prompt for your API key
- Set up data directories
- Check if your resume is ready

**Or manually:**

```bash
# Copy template
cp .env.example .env

# Edit file
nano .env  # or use your editor

# Add your API key
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

---

## 📝 First Run (10 minutes)

### Step 1: Create Your Profile

```bash
python -m src.main setup --resume "Elena Revicheva 03.11.2025 Resume.pdf"
```

**What happens:**
1. Extracts text from your PDF resume
2. Sends to Claude AI for analysis
3. Identifies your:
   - Skills and technologies
   - Work experience
   - Education
   - Key achievements
   - Years of experience
4. Saves to `data/profiles/profile.json`

**Time:** 30-60 seconds

**Output:**
```
✓ Profile setup complete!

Name: Elena Revicheva
Email: your@email.com
Location: Panama City, Panama
Skills: 45 skills detected
Experience: 10 years

Top Skills: Python, TypeScript, React, Claude, GPT, ...
```

### Step 2: Search for Jobs

```bash
python -m src.main search
```

**What happens:**
1. Searches LinkedIn for jobs matching your profile
2. Searches Indeed for jobs
3. Extracts job details (title, company, description)
4. Uses AI to score each job (0-100)
5. Filters by minimum score (default: 60)
6. Saves all jobs to `data/jobs/`

**Time:** 1-2 minutes

**Output:**
```
Found 47 matching jobs!

Top Job Matches:
╭───────┬─────────────┬────────────────────┬──────────╮
│ Score │ Company     │ Title              │ Location │
├───────┼─────────────┼────────────────────┼──────────┤
│ 92    │ StartupX    │ AI Engineer        │ Remote   │
│ 88    │ TechCorp    │ Founding Engineer  │ Remote   │
│ 85    │ AILab       │ ML Engineer        │ Remote   │
└───────┴─────────────┴────────────────────┴──────────┘
```

### Step 3: Apply to Jobs

```bash
python -m src.main apply --top 5
```

**What happens:**
1. Selects top 5 unapplied jobs by match score
2. For each job:
   - Generates tailored resume (emphasizes relevant skills)
   - Writes custom cover letter (personalized to company/role)
   - Saves both to local files
   - Tracks application in database
3. Shows you where to manually submit

**Time:** 2-3 minutes

**Output:**
```
Preparing applications for top 5 jobs:

1. StartupX - AI Engineer
   Match Score: 92
   ✅ Resume tailored
   ✅ Cover letter written
   ✓ Application prepared
   ⚠️ Manual submission required: https://...

2. TechCorp - Founding Engineer
   ...
```

### Step 4: Review Generated Content

```bash
# Check your tailored resumes
ls tailored_resumes/

# Check your cover letters
ls cover_letters/
```

**Important:** Always review AI-generated content before submitting!

### Step 5: Submit Applications

1. Open the job URL provided
2. Click "Apply" on the job site
3. Upload your tailored resume
4. Paste your cover letter
5. Fill out any additional forms
6. Submit!

---

## 🎯 Daily Workflow (15 minutes/day)

### Morning (5 min)

```bash
# Search for new jobs
python -m src.main search --limit 50

# Check what you found
python -m src.main status
```

### Afternoon (10 min)

```bash
# Generate materials for top 3-5 jobs
python -m src.main apply --top 5

# Review and submit applications
# (Open tailored_resumes/ and cover_letters/)
```

### Evening (Optional)

```bash
# Check follow-ups
python -m src.main followup

# Launch dashboard to review progress
python -m src.main dashboard
```

---

## 🎨 Using the Dashboard

```bash
# Start the dashboard
python -m src.main dashboard
```

Then open http://localhost:8000 in your browser.

**Features:**
- 📊 Real-time statistics
- 🎯 Top job matches
- 📈 Application funnel
- 📬 Follow-up reminders
- 💼 Full job listings

---

## 🔍 Understanding Match Scores

The AI scores each job from 0-100 based on:

### 90-100: Perfect Match ⭐⭐⭐⭐⭐
- **All key skills match**
- Experience level perfect fit
- Remote/location matches preferences
- Role aligns with targets
- Company stage/size fits
- **Action: Apply immediately!**

### 80-89: Excellent Match ⭐⭐⭐⭐
- Most skills match
- Experience level good fit
- Location acceptable
- Role type matches
- **Action: Definitely apply**

### 70-79: Good Match ⭐⭐⭐
- Many skills match
- Experience close enough
- Some compromises on requirements
- **Action: Apply if interested**

### 60-69: Okay Match ⭐⭐
- Some skills match
- May be stretch role
- Consider if few options
- **Action: Review carefully**

### Below 60: Weak Match ⭐
- Limited skill overlap
- Wrong experience level
- Location mismatch
- **Action: Usually skip**

---

## 💡 Pro Tips

### 1. Start Conservative

Your first run, use higher threshold:
```bash
python -m src.main search --min-score 75
```

After you see results, adjust if needed.

### 2. Review AI Output

**Always** read generated resumes and cover letters!
- Check for accuracy
- Add personal touches
- Fix any errors
- Ensure it sounds like you

### 3. Quality > Quantity

Better to send 5 great applications than 20 mediocre ones.

### 4. Use the Dashboard

Track your metrics:
- Response rate (aim for 5-15%)
- Application volume (10-20/week)
- Follow-up timing
- Best sources

### 5. Follow Up

```bash
# Check weekly
python -m src.main followup
```

Send follow-up emails 7 days after applying if no response.

### 6. Network in Parallel

Don't rely only on applications:
- Connect on LinkedIn
- Reach out to employees
- Attend virtual events
- Engage with companies on Twitter

### 7. Iterate Your Profile

As you learn what works:
```bash
# Update your profile
# Edit: data/profiles/profile.json
# Or re-run setup with updated resume
```

---

## 📊 Success Metrics

### Track These Numbers

**Weekly Goals:**
- 10-20 quality applications
- 1-3 responses/callbacks
- 5-10 LinkedIn connections
- 2-3 follow-ups sent

**Monthly Goals:**
- 40-80 applications
- 5-10 interviews
- 1-2 second rounds
- Continuous improvement

### Expected Timeline

- **Week 1-2**: Setup and testing (5-10 apps)
- **Week 3-4**: Full pipeline (15-20 apps/week)
- **Week 4-8**: First interviews start
- **Week 8-12**: Offers likely

Response rates vary by:
- Experience level
- Market conditions
- Location preferences
- Salary expectations

---

## 🐛 Troubleshooting

### "No profile found"

**Fix:**
```bash
python -m src.main setup --resume YOUR_RESUME.pdf
```

### "No jobs found"

**Possible causes:**
- Keywords too specific
- Min score too high
- Location too restrictive

**Fix:**
```bash
# Try broader search
python -m src.main search --min-score 60 --keywords "AI" "Engineer"
```

### "API key error"

**Fix:**
```bash
# Check .env file
cat .env | grep ANTHROPIC_API_KEY

# Should show: ANTHROPIC_API_KEY=sk-ant-...
```

### Scraper errors

**Possible causes:**
- Rate limiting by job sites
- Network issues
- Site structure changed

**Fix:**
- Wait 1 hour and try again
- Use VPN if needed
- Check logs/ for details

### Generated content looks off

**Fix:**
- Review and edit manually
- Update your profile with better info
- Try regenerating for different job

---

## 🎓 Learning Resources

### Understanding the System

1. **README.md** - Complete documentation
2. **QUICKSTART.md** - This file
3. **FEATURES.md** - Full feature list
4. **ARCHITECTURE.md** - Technical details

### Command Reference

```bash
# Setup
python -m src.main setup --resume FILE

# Search
python -m src.main search [--keywords K] [--location L] [--remote] [--limit N] [--min-score S]

# Apply
python -m src.main apply [--top N] [--auto]

# Status
python -m src.main status

# Follow-ups
python -m src.main followup

# Dashboard
python -m src.main dashboard [--port P]
```

### File Locations

```
Data Files:
- data/profiles/profile.json        # Your profile
- data/jobs/*.json                  # Discovered jobs
- data/applications/*.json          # Applications

Generated Content:
- tailored_resumes/*.md             # Custom resumes
- cover_letters/*.txt               # Cover letters

Logs:
- logs/app.log                      # Error logs
```

---

## 🎯 Your First Week Checklist

### Day 1: Setup
- [ ] Install dependencies
- [ ] Configure API key
- [ ] Create profile from resume
- [ ] Run first job search
- [ ] Review match scores

### Day 2: Test Applications
- [ ] Generate materials for 2-3 jobs
- [ ] Review quality of output
- [ ] Submit test applications
- [ ] Set up tracking system

### Day 3-5: Ramp Up
- [ ] Apply to 3-5 jobs daily
- [ ] Refine search parameters
- [ ] Improve profile if needed
- [ ] Start using dashboard

### Day 6-7: Optimize
- [ ] Analyze what's working
- [ ] Adjust match score threshold
- [ ] Network on LinkedIn
- [ ] Plan next week's strategy

---

## 🚀 Advanced Usage

Once comfortable, try:

### Scheduled Automation

```bash
# Add to crontab (Linux/Mac)
0 9 * * * cd /path/to/vibejobhunter && python -m src.main search --limit 50

# Or use Task Scheduler (Windows)
```

### Custom Searches

```bash
# Very targeted search
python -m src.main search \
  --keywords "LLM Engineer" "Founding Engineer" \
  --location "Remote" \
  --remote \
  --min-score 80 \
  --limit 100
```

### Batch Processing

```bash
# Search once per day
python -m src.main search --limit 100

# Apply to different batches
python -m src.main apply --top 5  # Monday
python -m src.main apply --top 5  # Tuesday
python -m src.main apply --top 5  # Wednesday
```

---

## 🎊 Success Stories

### Elena's Results (Example)

Built this tool and in the first month:
- 150 jobs discovered
- 45 applications sent
- 8 responses (18% response rate!)
- 5 interviews
- 2 second rounds
- **1 offer** 🎉

**Your results will vary** based on:
- Your experience level
- Market conditions
- Location preferences
- Job target specificity

---

## 🤝 Get Help

### Need Assistance?

1. Check README.md for details
2. Review logs/ for errors
3. Verify .env configuration
4. Try with fresh profile

### Community

- Star the repo ⭐
- Share your success
- Report bugs
- Suggest features

---

## 🎯 Final Thoughts

**Remember:**
- Consistency beats intensity
- Quality over quantity
- AI assists, you decide
- Follow up matters
- Network in parallel
- Stay positive!

**You've got this!** 💪

---

**Ready to start? Run:**

```bash
python setup.py
python -m src.main setup --resume YOUR_RESUME.pdf
python -m src.main search
python -m src.main apply --top 5
```

**Happy job hunting!** 🚀✨

Built with ❤️ for Elena Revicheva and all job seekers.
