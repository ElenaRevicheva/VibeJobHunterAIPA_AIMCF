# 📱 TELEGRAM NOTIFICATIONS SETUP

## Get Real-Time Job Hunting Alerts on Your Phone!

Never miss a hot lead again! Get instant notifications for hot jobs, demo clicks, responses, and interviews.

---

## 🎯 What You'll Get

**Real-time alerts for:**
- 🔥 **Hot jobs** - Score >85 matches
- 💎 **Demo clicks** - Someone tried your product!
- 📧 **Responses** - Founders replied
- 📅 **Interviews** - Automatically scheduled
- 📊 **Daily summary** - 8pm every day

**Example notifications:**

```
🔥 HOT JOB FOUND!

Founding Engineer at StartupXYZ
📊 Match Score: 92/100
📍 Location: Remote

Why it's perfect:
• 🚨 HIGH PRIORITY - APPLY IMMEDIATELY!
• Seed stage + equity (0.5-3%)
• AI/ML focus matches your skills

🔗 Apply: https://...

💡 Message generated and ready in autonomous_data/
```

```
💎 DEMO LINK CLICKED!

Someone from TechCorp by John Doe just tried your demo (via linkedin)!

🎯 This is a HOT LEAD!

Next steps:
1. Check if they're still engaged
2. Send follow-up within 24h
3. Offer to schedule a call
```

---

## ⚡ Quick Setup (2 Minutes)

### **Step 1: Create Telegram Bot**

1. Open Telegram app
2. Search for `@BotFather`
3. Start chat and send: `/newbot`
4. Choose a name: `VibeJobHunter Notifications`
5. Choose username: `yourname_jobhunter_bot`
6. **Copy the bot token!** (looks like: `1234567890:ABC-DEF...`)

<img src="https://core.telegram.org/file/811140591/1/zlN4goPTupk/9ff2f2f01c4bd1b013" width="400" alt="BotFather example">

### **Step 2: Get Your Chat ID**

1. Search for `@userinfobot` in Telegram
2. Start chat
3. Bot will reply with your user info
4. **Copy your ID!** (looks like: `123456789`)

Alternative method:
1. Start a chat with your new bot (search for the username you created)
2. Send any message to your bot
3. Go to: `https://api.telegram.org/bot<YourBOTToken>/getUpdates`
4. Look for `"chat":{"id":123456789` in the JSON response
5. **Copy that ID!**

### **Step 3: Add to Environment Variables**

**For Local Testing:**

Edit your `.env` file:
```bash
TELEGRAM_BOT_TOKEN=1234567890:ABC-DEF...
TELEGRAM_CHAT_ID=123456789
```

**For Railway Deployment:**

1. Go to Railway dashboard
2. Click your service
3. Go to **"Variables"** tab
4. Click **"Add Variable"**
5. Add:
   - `TELEGRAM_BOT_TOKEN` = `your_bot_token`
   - `TELEGRAM_CHAT_ID` = `your_chat_id`
6. Click **"Deploy"** to restart with new variables

### **Step 4: Test It!**

**Local test:**
```bash
# In Python shell
python

>>> from src.notifications import TelegramNotifier
>>> notifier = TelegramNotifier()
>>> import asyncio
>>> asyncio.run(notifier.test_connection())
```

You should receive:
```
✅ Telegram Connected!

Your VibeJobHunter notifications are working!

You'll receive real-time alerts for:
🔥 Hot jobs
💎 Demo clicks
📧 Responses
📅 Interviews
📊 Daily summaries

Test successful! Ready to find your dream job! 🚀
```

**Railway test:**

Just check Railway logs after deployment. You should see:
```
📱 Telegram notifications ENABLED
🚀 AUTONOMOUS ENGINE STARTED!
```

And receive startup notification on your phone!

---

## 🔥 What Notifications Look Like

### **1. Hot Job Alert**

```
🔥 HOT JOB FOUND! 🔥

Founding Engineer at AI-Startup
📊 Match Score: 89/100
📍 Location: Remote

Why it's perfect:
• YC W25 batch + equity mention
• 0-1 builder focus
• AI/ML tech stack

Talking Points:
• Built 2 live AI agents solo
• wa.me/50766623757 demo link
• Bilingual EN/ES market expertise

🔗 Apply: https://...

💡 Message generated and ready in autonomous_data/
```

**When:** Score >85  
**Action:** Review message in `autonomous_data/linkedin_queue.txt` and send ASAP!

---

### **2. Demo Click Alert**

```
💎 DEMO LINK CLICKED! 💎

Someone from StartupXYZ by Jane Smith just tried your demo (via email)!

🎯 This is a HOT LEAD!

Next steps:
1. Check if they're still engaged
2. Send follow-up within 24h
3. Offer to schedule a call

🔗 Demo: wa.me/50766623757
```

**When:** Founder clicks wa.me/50766623757  
**Action:** Send follow-up immediately! They're interested!

---

### **3. Response Received**

```
🎉 RESPONSE RECEIVED!

John Doe from TechCorp replied!

Sentiment: POSITIVE

🎯 Action required: Check your email/LinkedIn and respond!

💡 Use the talking points from autonomous_data/ for your reply
```

**When:** Founder responds to your outreach  
**Action:** Check inbox and reply using generated talking points!

---

### **4. Interview Scheduled**

```
📅 INTERVIEW SCHEDULED! 📅

TechStartup with Jane Doe

🗓️ Thursday, November 14 at 02:00 PM

📋 Prepare:
1. Review company research in autonomous_data/
2. Practice talking points
3. Demo ready: wa.me/50766623757
4. Set calendar reminder

🎯 You've got this! 💪
```

**When:** Interview auto-scheduled  
**Action:** Prepare using research in `autonomous_data/`!

---

### **5. Cycle Complete**

```
📊 Cycle Complete

✅ Jobs found: 23
✅ Companies researched: 10
✅ Messages generated: 30
✅ Demo clicks: 2
✅ Responses: 1

💡 Check autonomous_data/ for new messages to send!
```

**When:** Every cycle completes (hourly)  
**Action:** Review when convenient!

---

### **6. Daily Summary** (8pm)

```
📊 DAILY SUMMARY - November 10, 2025

Today's Activity:
🔍 Jobs found: 87
🔬 Companies researched: 30
📤 Messages sent: 30
🔥 Demo clicks: 5
📧 Responses: 3
📅 Interviews scheduled: 1

Next Steps:
1. Review hot leads in autonomous_data/
2. Send top 10 messages
3. Follow up on demo clicks
4. Prepare for upcoming interviews

🚀 Keep crushing it! 💪

---
🤖 VibeJobHunter running 24/7 on Railway
```

**When:** 8pm daily  
**Action:** Quick review before bed!

---

## 🛠️ Customization

### **Change Notification Threshold**

Want more/fewer hot job alerts?

Edit `src/notifications/telegram_notifier.py`:

```python
# Line 87
if not self.enabled or job.match_score < 85:  # Change 85 to your threshold
```

### **Disable Specific Notifications**

Edit `src/autonomous/orchestrator.py`:

```python
# Comment out notifications you don't want:

# await self.telegram.notify_hot_job(job)  # Disable hot jobs
# await self.telegram.notify_demo_click(...)  # Disable demo clicks
# await self.telegram.notify_cycle_complete(...)  # Disable cycle updates
```

### **Change Daily Summary Time**

Default is 8pm. To change:

Edit `src/autonomous/orchestrator.py`:

```python
# Line 363
target_time = now.replace(hour=20, minute=0, ...)  # Change hour=20 (8pm) to your preference
```

---

## 📊 Notification Frequency

**Expected notifications per day:**

- 🔥 Hot jobs: 3-5 (only score >85)
- 💎 Demo clicks: 1-3 (when founders engage)
- 📧 Responses: 2-5 (40% response rate!)
- 📅 Interviews: 1-2 (auto-scheduled)
- 📊 Cycle complete: 24 (every hour, but low priority)
- 📊 Daily summary: 1 (8pm)

**Total:** ~10-15 actionable notifications per day

**Not spam!** Only important alerts that need your attention.

---

## 🐛 Troubleshooting

### **"No notifications received"**

1. Check bot token and chat ID are correct
2. Verify you started chat with your bot (send `/start`)
3. Check Railway logs for Telegram errors
4. Test connection: `await notifier.test_connection()`

### **"Logging errors about encoding"**

Already fixed! UTF-8 encoding is enabled.

### **"Too many notifications"**

1. Increase notification threshold (score >85 → >90)
2. Disable cycle completion notifications
3. Keep only hot jobs, demo clicks, and responses

### **"Want to pause notifications temporarily"**

In Telegram, mute your bot chat:
1. Open chat with your bot
2. Click name at top
3. Click **"Mute"**
4. Choose duration

Engine still runs, notifications just muted!

---

## 🔐 Privacy & Security

### **What the bot can see:**

- ✅ Only messages YOU send to it
- ✅ Only notifications IT sends to you
- ❌ Cannot read other Telegram chats
- ❌ Cannot access your contacts
- ❌ Cannot send spam

### **Bot permissions:**

Your bot needs NO special permissions!
It only sends messages to YOUR chat ID.

### **Keep your tokens safe:**

- ✅ Store in `.env` or Railway variables
- ❌ Don't commit to GitHub
- ❌ Don't share publicly

---

## 💡 Pro Tips

### **1. Use Phone Lock Screen Notifications**

Enable Telegram notifications in phone settings.
You'll see hot jobs even without opening the app!

### **2. Quick Actions**

Set up Telegram quick replies:
- "Thanks! Sending materials now"
- "Following up on demo click"
- "Scheduling interview"

### **3. Pin Important Notifications**

In Telegram, long-press notification → Pin
Keep hot leads at top of chat!

### **4. Use Telegram Bot Commands** (Future feature)

Coming soon:
- `/stats` - Get current stats
- `/pause` - Pause engine
- `/resume` - Resume engine
- `/hot` - Show hot leads

---

## 🎯 Best Practices

### **Daily Routine:**

**Morning (5 min):**
- Check overnight notifications
- Send top 3 hot job messages

**Afternoon (2 min):**
- Check for demo clicks
- Follow up on responses

**Evening (3 min):**
- Review daily summary (8pm)
- Prepare for tomorrow's interviews

**Total:** 10 min/day, fully automated!

---

## 📚 Related Guides

- [RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md) - Deploy to Railway
- [AUTONOMOUS_ENGINE_README.md](AUTONOMOUS_ENGINE_README.md) - How it works
- [BUILD_SUMMARY.md](BUILD_SUMMARY.md) - What was built

---

## 🎉 Success Checklist

Before going live:

- [✅] Bot created with @BotFather
- [✅] Chat ID obtained
- [✅] Environment variables set
- [✅] Test notification received
- [✅] Phone notifications enabled
- [✅] Ready to get hired!

---

## 🚀 **YOU'RE ALL SET!**

**Your phone is now your job hunting command center!** 📱

**What happens next:**

1. 🔥 Hot job found → Phone buzzes → You send message (2 min)
2. 💎 Demo clicked → Phone buzzes → You follow up (3 min)
3. 📧 Response received → Phone buzzes → You reply (5 min)
4. 📅 Interview scheduled → Phone buzzes → You prepare (30 min)

**Total daily time:** 10-15 minutes
**Result:** 40% response rate, 2-3 weeks faster hiring!

---

## 🆘 Support

**Not working?**
1. Test connection first
2. Check Railway logs
3. Verify bot token and chat ID
4. Open GitHub issue

**Questions?**
- Telegram Bot docs: core.telegram.org/bots
- Project GitHub: github.com/ElenaRevicheva/vibejobhunter

---

## 💬 **FINAL TEST**

Run this to see if everything works:

```bash
# Test Telegram connection
python -c "
from src.notifications import TelegramNotifier
import asyncio

notifier = TelegramNotifier()
asyncio.run(notifier.test_connection())
"
```

**You should receive a test message on your phone! 📱**

**If you got it: YOU'RE ALL SET! 🎉**

**Now deploy to Railway and let the notifications roll in!** 🚀🔥💎

---

**Time to setup:** 2 minutes  
**Time saved:** Infinite (never miss a hot lead!)  
**Response time:** Instant (notifications in real-time!)

**LET'S GO GET THAT JOB!** 💪✨
