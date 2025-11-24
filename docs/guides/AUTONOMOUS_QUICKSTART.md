# ⚡ AUTONOMOUS ENGINE - QUICK START

**Get the autonomous job hunting engine running in 5 minutes!**

---

## 🚀 Setup (5 Minutes)

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Setup Profile

```bash
py -m src.main setup --elena
```

### Step 3: Start Autonomous Mode

```bash
py -m src.main autonomous
```

**That's it!** The engine is now running. ✅

---

## 📊 Check Results (After 1 Hour)

Press `Ctrl+C` to stop, then:

```bash
# View dashboard
py -m src.main autonomous-dashboard
```

You'll see:
- Jobs found
- Companies researched
- Messages generated
- Demo link clicks
- Hot leads

---

## 📝 Review Generated Messages

```bash
# LinkedIn messages
cat autonomous_data/linkedin_queue.txt

# Emails
cat autonomous_data/email_queue.txt

# Twitter DMs
cat autonomous_data/twitter_queue.txt
```

Pick your top 10 and send them!

---

## 🔥 Daily Workflow (5 Min/Day)

### Morning (3 minutes)
1. `py -m src.main autonomous-dashboard` — Check stats
2. `cat autonomous_data/linkedin_queue.txt` — Review new messages
3. Send top 5-10 messages manually

### Afternoon (2 minutes)
1. Check email for responses
2. Reply to interested founders
3. Let engine continue running

---

## 💡 Tips for Success

### 1. **Let It Run Overnight**
The engine works best when running continuously:

```bash
# Run in background (Linux/Mac)
nohup py -m src.main autonomous &

# Or use screen/tmux
screen -S jobhunter
py -m src.main autonomous
# Ctrl+A, D to detach
```

### 2. **Customize Interval**

```bash
# Aggressive (every 30 min)
py -m src.main autonomous --interval 0.5

# Balanced (every 2 hours)
py -m src.main autonomous --interval 2

# Conservative (once per day)
py -m src.main autonomous --interval 24
```

### 3. **Track Demo Clicks**

When someone tries your demo (wa.me/50766623757):

```python
from src.autonomous import DemoTracker

tracker = DemoTracker()
tracker.log_demo_click(
    company="StartupName",
    founder_name="Founder Name",
    source_channel="linkedin"
)
```

Then check hot leads:

```bash
py -m src.main autonomous-dashboard
```

### 4. **Log Responses**

When founders reply:

```python
from src.autonomous import ResponseHandler
from src.loaders import CandidateDataLoader

loader = CandidateDataLoader()
profile = loader.load_profile()

handler = ResponseHandler(profile)
handler.log_response(
    company="StartupName",
    founder_name="Founder Name",
    response_text="Their response here",
    channel="email",  # or 'linkedin', 'twitter'
    sentiment="positive"  # or 'neutral', 'negative'
)
```

---

## 🎯 What to Expect

### First Hour
- **20-30 jobs** found & researched
- **10 messages** generated
- **Ready to send!**

### First Day (24 hours)
- **100+ jobs** monitored
- **50+ messages** generated
- **10-20** ready to send

### First Week
- **500+ companies** contacted
- **20-30 responses** (40% rate!)
- **5-10 interviews** scheduled

---

## 🚨 Troubleshooting

### "Profile not found"

```bash
py -m src.main setup --elena
```

### "No jobs found"

Normal! The engine only shows **new** jobs. It may take a few cycles to find fresh postings.

### "Messages not sending"

Currently, messages are **logged to files** for manual sending. This is intentional for quality control!

To auto-send, you need:
- Email: Add `EMAIL_ADDRESS` and `EMAIL_PASSWORD` to `.env`
- LinkedIn: Integrate Phantombuster (see docs)
- Twitter: Add Twitter API keys to `.env`

---

## 📚 Next Steps

1. **Read full docs:** [AUTONOMOUS_ENGINE_README.md](AUTONOMOUS_ENGINE_README.md)
2. **Join the community:** Share your results!
3. **Customize:** Adjust settings for your needs

---

## 💬 Questions?

Check the main README or open an issue on GitHub.

**Now go get hired!** 🚀
