# 🪟 VibeJobHunter - Windows Setup

**Complete setup guide for Windows users**

---

## ⚡ QUICK START (5 minutes)

### 1. Install Python (if needed)

**Check if you have Python:**
```cmd
python --version
```

**If not:**
1. Go to: https://www.python.org/downloads/
2. Download Python 3.9 or higher
3. Run installer
4. ✅ **IMPORTANT: Check "Add Python to PATH"**
5. Click "Install Now"

---

### 2. Clone Repository

**Open Command Prompt (Win+R → type `cmd` → Enter)**

```cmd
D:
cd \
mkdir projects
cd projects
git clone https://github.com/ElenaRevicheva/vibejobhunter.git
cd vibejobhunter
```

You're now in: `D:\projects\vibejobhunter\`

---

### 3. Run Autopilot

```cmd
vibe.bat
```

**That's it!** The script will:
- ✅ Check Python installation
- ✅ Install dependencies (first time only)
- ✅ Ask for your API key (first time only)
- ✅ Find your resume automatically
- ✅ Run full autopilot
- ✅ Open jobs in your browser

---

## 🔑 Get API Key (30 seconds)

Before running `vibe.bat`, get your API key:

1. Visit: https://console.anthropic.com/
2. Sign up (free tier available)
3. Click "Get API Keys"
4. Generate new key
5. Copy it (starts with `sk-ant-`)

When `vibe.bat` asks, paste it in.

---

## 📝 Daily Workflow

### Every Morning (15 minutes):

```cmd
D:
cd \projects\vibejobhunter
vibe.bat
```

Then:
1. ☕ Make coffee while AI works (5 min)
2. 📝 Review generated materials (2 min)
3. 🚀 Click Submit on 10 jobs (8 min)
4. ✅ Done for the day!

---

## 📊 Check Your Stats

```cmd
python -m src.main status
```

See:
- Total jobs discovered
- Applications sent
- Response rate
- Match scores

---

## 📬 Check Follow-ups

```cmd
python -m src.main followup
```

Shows which applications need follow-up emails.

---

## 🎯 Alternative: PowerShell Users

If you prefer PowerShell:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
.\vibe.bat
```

---

## 🐛 Troubleshooting

### "Python not found"
**Solution:**
1. Reinstall Python from python.org
2. ✅ Check "Add Python to PATH"
3. Restart Command Prompt

### "Git not found"
**Solution:**
1. Install Git: https://git-scm.com/download/win
2. Restart Command Prompt

### "No resume found"
**Solution:**
- Make sure your resume PDF is in `D:\projects\vibejobhunter\`
- Name it something with "resume" in the filename
- Example: `Elena_Resume.pdf` or `My_Resume_2025.pdf`

### "Module not found"
**Solution:**
```cmd
python -m pip install -r requirements.txt
```

### API Key Error
**Solution:**
1. Open `.env` file with Notepad
2. Make sure it says: `ANTHROPIC_API_KEY=sk-ant-your-key-here`
3. No spaces, no quotes

---

## 📁 File Locations

After running:
- **Tailored Resumes:** `D:\projects\vibejobhunter\tailored_resumes\`
- **Cover Letters:** `D:\projects\vibejobhunter\cover_letters\`
- **Your Profile:** `D:\projects\vibejobhunter\data\profiles\profile.json`
- **Applications:** `D:\projects\vibejobhunter\data\applications\`

---

## 💡 Pro Tips

### Create Desktop Shortcut

1. Right-click on `vibe.bat`
2. Send to → Desktop (create shortcut)
3. Double-click shortcut every morning

### Add to Startup

Create file: `start_vibe.bat`
```cmd
@echo off
timeout /t 300 /nobreak
D:
cd \projects\vibejobhunter
start cmd /k vibe.bat
```

Add to:
- `C:\Users\YourName\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\`

---

## 🎨 Windows Terminal (Optional)

For better experience, use **Windows Terminal** (free from Microsoft Store)

Then run:
```cmd
wt -d D:\projects\vibejobhunter vibe.bat
```

---

## 🚀 Quick Command Reference

```cmd
# Run autopilot
vibe.bat

# Check status
python -m src.main status

# Check follow-ups
python -m src.main followup

# Launch dashboard
python -m src.main dashboard

# Manual search
python -m src.main search --keywords "AI Engineer" --remote

# Manual apply
python -m src.main apply --top 5
```

---

## 📅 Recommended Schedule

### Daily (15 min):
```cmd
vibe.bat
```

### Monday (5 min):
```cmd
python -m src.main followup
```

### Friday (2 min):
```cmd
python -m src.main status
```

---

## 🎯 Expected Results

**Week 1:** 50 applications → 0-2 responses  
**Week 2-3:** 100 apps → 5-8 responses  
**Week 4-6:** 150 apps → 10-15 interviews  
**Week 6-8:** 200+ apps → Multiple offers 🎉

---

## 🆘 Need Help?

1. Check error message carefully
2. Try restarting Command Prompt
3. Make sure Python is in PATH
4. Verify API key in `.env` file
5. Check `logs\` folder for details

---

## 🌟 You're Ready!

```cmd
D:
cd \projects\vibejobhunter
vibe.bat
```

**Your AI engineering role starts now!** 🚀

---

*Built for Windows users who want to get hired fast.* ✨
