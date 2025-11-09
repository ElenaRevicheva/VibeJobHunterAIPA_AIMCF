# 🚀 VibeJobHunter - Quick Start Guide

Get up and running in 5 minutes!

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Configure API Keys

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your Anthropic API key
nano .env  # or use your favorite editor
```

**Minimum required:**
```
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

Get your API key from: https://console.anthropic.com/

## Step 3: Create Your Profile

```bash
python -m src.main setup --resume "Elena Revicheva 03.11.2025 Resume.pdf"
```

This takes about 30 seconds as Claude analyzes your resume.

## Step 4: Search for Jobs

```bash
# Quick search with defaults
python -m src.main search

# Or customize
python -m src.main search \
  --keywords "AI Engineer" "Founding Engineer" \
  --location "Remote" \
  --remote \
  --min-score 70
```

This will:
- Search LinkedIn & Indeed
- Score jobs against your profile
- Save top matches

## Step 5: Review & Apply

```bash
# See what was found
python -m src.main status

# Apply to top matches
python -m src.main apply --top 5
```

For each job, the system will:
- Generate a tailored resume
- Write a custom cover letter
- Save everything to local files
- Track the application

## Step 6: Monitor Progress

```bash
# Launch web dashboard
python -m src.main dashboard
```

Then open: http://localhost:8000

---

## 🎯 Daily Workflow

**Morning routine (5 minutes):**
```bash
# Search for new jobs
python -m src.main search --limit 50 --min-score 65

# Check status
python -m src.main status
```

**Apply to jobs (15 minutes):**
```bash
# Generate materials for top matches
python -m src.main apply --top 5

# Review generated resumes/cover letters in:
#   - tailored_resumes/
#   - cover_letters/

# Manually submit to job sites
```

**Check follow-ups (2 minutes):**
```bash
python -m src.main followup
```

---

## 📊 Understanding Match Scores

- **90-100**: Perfect match - Apply immediately!
- **80-89**: Excellent match - Strong candidate
- **70-79**: Good match - Worth applying
- **60-69**: Okay match - Review carefully
- **< 60**: Weak match - Skip unless specific reason

---

## 💡 Pro Tips

### 1. Start Conservative
```bash
# First run: high threshold
python -m src.main search --min-score 75

# After reviewing, lower if needed
python -m src.main search --min-score 65
```

### 2. Batch Process
```bash
# Search once, apply multiple times
python -m src.main search --limit 100
python -m src.main apply --top 3  # Day 1
python -m src.main apply --top 3  # Day 2
python -m src.main apply --top 3  # Day 3
```

### 3. Review Before Sending
Always read the generated materials! AI is smart but you know your story best.

### 4. Track Everything
```bash
# Update application status manually
# Edit: data/applications/{job_id}.json
# Change "status": "applied" to "interviewing"
```

### 5. Follow Up
Set calendar reminders to follow up after 7 days if no response.

---

## 🐛 Common Issues

### "No profile found"
→ Run `setup` command first

### "No jobs found"
→ Try broader keywords or lower min-score

### Scraper errors
→ LinkedIn/Indeed may rate-limit. Wait 1 hour or use VPN

### API errors
→ Check your ANTHROPIC_API_KEY in .env

---

## 🎨 Customization

### Edit Your Preferences

`src/core/config.py`:
```python
target_roles = [
    "AI Engineer",
    "Your Custom Role",
    # Add more...
]

target_keywords = [
    "AI", "Python", "React",
    # Your keywords...
]
```

### Change Daily Limits

`.env`:
```
MAX_DAILY_APPLICATIONS=20
```

---

## 📈 Success Metrics

Track your progress:
- **Week 1**: Set up, test with 5-10 applications
- **Week 2**: Ramp to 10-15 applications/week
- **Week 3+**: Maintain 15-20 quality applications/week
- **Expected**: 5-10% response rate (interviews)
- **Goal**: Land offer within 4-8 weeks

---

## 🆘 Need Help?

1. Check README.md for full documentation
2. Review generated files in `tailored_resumes/` and `cover_letters/`
3. Check `logs/` for error details
4. Ensure .env file has correct API keys

---

## 🚀 Next Steps

Once comfortable:
1. Customize job search parameters
2. Add more platforms (coming soon)
3. Set up daily cron job for automated searches
4. Network in parallel on LinkedIn
5. Track all interactions in the dashboard

---

**Happy hunting! Your next role is just around the corner.** ✨

Built with ❤️ for Elena Revicheva's job search.
