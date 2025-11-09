# 🧪 TESTING CHECKLIST - VibeJobHunter Complete System

**Before we start applying to real jobs, let's test each feature!**

---

## ✅ PRE-TEST SETUP

### 1. Check Dependencies
```bash
cd /workspace
pip install -r requirements.txt
```

Expected: All packages installed successfully

### 2. Verify API Key
```bash
cat .env | grep ANTHROPIC_API_KEY
```

Expected: Should show your API key (not empty)

---

## 🧪 TEST PHASE 1: Profile & Smart Matching

### Test 1.1: Elena Profile Loading
```bash
python -m src.main setup --elena
```

**Expected output:**
- ✅ Profile loaded instantly
- Shows: Name, Email, Location, Skills, Experience
- Ready message with next steps

**Success criteria:**
- Takes < 5 seconds
- No errors
- Profile data looks correct

---

### Test 1.2: Profile Loaded Correctly
Check the saved profile:
```bash
cat data/profile.json | head -50
```

**Expected:**
- Name: Elena Revicheva
- Email: aipa@aideazz.xyz
- Skills include: Python, TypeScript, AI, etc.
- Experience: 7+ years

---

## 🧪 TEST PHASE 2: Batch Apply (Full Workflow)

### Test 2.1: Create Test Job URLs File
Create `test_jobs.txt` with 3 jobs:
```bash
cat > test_jobs.txt << 'EOF'
https://linkedin.com/jobs/view/4100549873
https://linkedin.com/jobs/view/4081447878
https://indeed.com/viewjob?jk=abc123
EOF
```

**Note:** Use real job URLs you find! These are just examples.

---

### Test 2.2: Run Batch Apply V2
```bash
python -m src.main batch --file test_jobs.txt --v2
```

**Expected behavior:**
1. **Fetching:** Shows progress bar, fetches 3 jobs
2. **Scoring:** AI scores each job
3. **Filtering:** Applies smart criteria + red flag detection
4. **Materials:** Generates resume + cover letter + interview prep
5. **Browser:** Opens job tabs
6. **Summary:** Shows stats and file locations

**Success criteria:**
- No Python errors
- All 3 jobs fetched (or shows specific errors for failed ones)
- Materials generated for successful jobs
- Shows interview_prep/ folder
- Browser tabs open
- Can see API usage stats

---

### Test 2.3: Verify Generated Files

#### Check Resumes
```bash
ls -lh resumes/
cat resumes/*.md | head -50
```

**Expected:**
- 1 file per successful job
- Contains Elena's name and info
- Includes live demo link (wa.me/50766623757)
- Tailored to job requirements

#### Check Cover Letters
```bash
ls -lh cover_letters/
cat cover_letters/*.txt | head -30
```

**Expected:**
- 1 file per job
- Personalized opening
- Mentions company name
- Includes demo link

#### Check Interview Prep
```bash
ls -lh interview_prep/
cat interview_prep/*.md | head -100
```

**Expected:**
- 1 file per job (15-20 pages each)
- Company name in title
- Custom questions
- Talking points
- Salary scripts

---

## 🧪 TEST PHASE 3: Dashboard & Tracking

### Test 3.1: View Dashboard
```bash
python -m src.main dashboard
```

**Expected output:**
- Shows application stats
- Total, applied, interviewing, offers
- Progress bar toward target (50)
- Recent applications table
- Status breakdown

**Success criteria:**
- Shows your test applications
- Metrics look correct
- No errors

---

### Test 3.2: Export Summary
```bash
python -m src.main dashboard --export
cat job_hunt_summary.md
```

**Expected:**
- Creates `job_hunt_summary.md`
- Contains overview stats
- Lists recent applications

---

## 🧪 TEST PHASE 4: Follow-Ups

### Test 4.1: Check Follow-Up Schedule
```bash
python -m src.main followup
```

**Expected output (if applications are new):**
- "No follow-ups needed today!"

**OR (if 3+ days old):**
- Shows list of applications needing follow-up
- Displays email templates
- Shows days since application

**Success criteria:**
- No errors
- Logic makes sense (3+ days = follow-up)

---

### Test 4.2: Check Schedule File
```bash
cat data/follow_up_schedule.json
```

**Expected:**
- JSON with application IDs
- Follow-up dates for each
- Company names and roles

---

## 🧪 TEST PHASE 5: End-to-End Integration

### Test 5.1: Complete Workflow Test

**Scenario:** Apply to 1-2 REAL jobs you're interested in

1. **Find jobs:**
   ```bash
   # Add real job URLs to test_jobs_real.txt
   ```

2. **Setup:**
   ```bash
   python -m src.main setup --elena
   ```

3. **Apply:**
   ```bash
   python -m src.main batch --file test_jobs_real.txt --v2
   ```

4. **Review materials:**
   - Read generated resume
   - Read cover letter
   - Skim interview prep

5. **Submit one application manually:**
   - Copy resume content
   - Copy cover letter
   - Paste into job application
   - Submit!

6. **Check dashboard:**
   ```bash
   python -m src.main dashboard
   ```

**Success criteria:**
- ✅ Materials are high quality
- ✅ Resume looks professional
- ✅ Cover letter is personalized
- ✅ Interview prep is useful
- ✅ Demo link is prominent
- ✅ Easy to copy-paste and submit

---

## 🎯 QUALITY CHECKS

### Resume Quality
- [ ] Professional format
- [ ] Tailored to job
- [ ] Live demo link prominent
- [ ] Skills match job requirements
- [ ] No typos or errors

### Cover Letter Quality
- [ ] Addresses company specifically
- [ ] Mentions job title
- [ ] Highlights relevant experience
- [ ] Includes demo link
- [ ] Strong call-to-action

### Interview Prep Quality
- [ ] Company name in title
- [ ] Custom talking points
- [ ] Relevant technical discussion
- [ ] Questions to ask them
- [ ] Salary negotiation script
- [ ] Closing statement

### Portfolio Integration
- [ ] wa.me/50766623757 in resume
- [ ] wa.me/50766623757 in cover letter
- [ ] "Try it now!" call-to-action
- [ ] Relevant projects highlighted

---

## ⚠️ KNOWN ISSUES TO WATCH FOR

### Potential Issues:
1. **Job scraping fails:** Some sites block scrapers
   - **Solution:** Try different job URLs
   
2. **API rate limits:** If processing many jobs
   - **Solution:** Built-in rate limiting should handle this
   
3. **Browser doesn't open:** OS-specific
   - **Solution:** Manually open URLs (shown in output)
   
4. **Interrupt during batch:** Connection issues
   - **Solution:** Use `--resume` flag to continue

---

## 📊 SUCCESS METRICS

After testing, you should have:
- ✅ Profile loaded (< 5 seconds)
- ✅ 3+ test applications created
- ✅ Custom materials for each
- ✅ Interview prep files generated
- ✅ Follow-ups scheduled
- ✅ Dashboard shows progress
- ✅ No critical errors

**If all tests pass → Ready for production use!**

---

## 🚀 AFTER TESTING

### If tests pass:
1. Delete test applications
2. Create fresh `jobs.txt` with real targets
3. Start daily workflow:
   - Find 10-20 jobs per day
   - Run batch apply
   - Submit applications
   - Check dashboard
   - Send follow-ups 2x per week

### If tests fail:
1. Check error messages
2. Review logs in `logs/`
3. Verify API key is set
4. Check dependencies installed
5. Try with single job URL first

---

## 💡 TESTING TIPS

1. **Start small:** Test with 1-2 jobs first
2. **Real URLs:** Use actual job postings
3. **Review output:** Read generated materials before submitting
4. **Check logs:** If errors, check `logs/` folder
5. **Iterate:** Adjust and improve based on results

---

## ✅ FINAL CHECKLIST

Before going live:
- [ ] Profile setup works
- [ ] Batch apply completes successfully
- [ ] Materials are high quality
- [ ] Demo links are prominent
- [ ] Interview prep is useful
- [ ] Dashboard shows accurate data
- [ ] Follow-ups are scheduled
- [ ] No critical errors

**All checked? You're ready to hunt! 🚀**

---

## 📞 NEXT STEPS AFTER TESTING

1. **Daily workflow:**
   ```bash
   # Morning: Find jobs, create jobs.txt
   python -m src.main batch --file jobs.txt --v2
   # Submit applications
   python -m src.main dashboard
   ```

2. **Weekly follow-ups:**
   ```bash
   python -m src.main followup
   # Send emails
   ```

3. **Interview prep:**
   ```bash
   # Check interview_prep/[Company].md before each interview
   ```

**Let's get you hired! 🎉**
