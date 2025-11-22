# 💼 LinkedIn CMO (Chief Marketing Officer) - User Guide

## ✅ What Was Added

The LinkedIn CMO is a new feature that automates LinkedIn content generation and posting via Make.com webhook.

### Files Created/Modified:
1. ✅ **NEW**: `src/notifications/linkedin_cmo.py` - LinkedIn content automation
2. ✅ **MODIFIED**: `src/notifications/__init__.py` - Added LinkedInCMO import (2 lines)
3. ✅ **MODIFIED**: `.env.example` - Added webhook URL example (3 lines)

### What Was NOT Touched:
- ❌ Job search functionality (scrapers, agents, core, etc.)
- ❌ Telegram notifications (still works exactly the same)
- ❌ Main CLI (`src/main.py`)
- ❌ Batch application system
- ❌ Any other existing features

## 🚀 Quick Start

### 1. Get Your Make.com Webhook URL

1. Go to [Make.com](https://www.make.com) and create an account
2. Create a new scenario
3. Add a Webhook trigger (first step)
4. Copy the webhook URL (looks like: `https://hook.us2.make.com/xyz123...`)

### 2. Configure Environment

Add to your `.env` file:

```bash
MAKE_WEBHOOK_URL_LINKEDIN=https://hook.us2.make.com/your_webhook_id_here
```

### 3. Use LinkedIn CMO

```python
import asyncio
from src.notifications import LinkedInCMO

async def main():
    # Initialize CMO
    cmo = LinkedInCMO()
    
    # Generate and preview a post (doesn't send)
    preview = cmo.preview_post(
        post_type='open_to_work',
        language='en',  # or 'es' for Spanish
        role='Founding Engineer',
        experience='building AI tools for 3 years',
        demo_link='https://wa.me/50766623757'
    )
    print(preview)
    
    # Generate and send a post
    await cmo.post_open_to_work(
        role='Founding Engineer',
        experience='building AI automation tools',
        demo_link='https://wa.me/50766623757'
    )

asyncio.run(main())
```

## 📝 Post Types

### 1. Open to Work
Announce you're looking for opportunities:

```python
await cmo.post_open_to_work(
    role='Founding Engineer',
    experience='building AI tools for 3 years',
    skill_1='Build 0→1 products',
    skill_2='Lead technical architecture',
    skill_3='Ship fast with quality',
    demo_link='https://wa.me/50766623757'
)
```

### 2. Achievement
Share wins and milestones:

```python
await cmo.post_achievement(
    achievement_description='Launched my AI job hunting automation!',
    learning_1='Start with MVP',
    learning_2='User feedback is gold',
    learning_3='Ship early and often',
    demo_link='https://wa.me/50766623757'
)
```

### 3. Insight
Share valuable insights:

```python
await cmo.post_insight(
    project='an AI automation tool',
    main_insight='AI can save 10+ hours per week on repetitive tasks',
    reason_1='Reduces manual work',
    reason_2='Increases accuracy',
    reason_3='Scales effortlessly'
)
```

### 4. Demo Share
Share your latest project:

```python
await cmo.post_demo(
    project_name='VibeJobHunter',
    description='AI-powered job search automation that finds and applies to jobs 24/7',
    tech_1='Python',
    tech_2='Claude AI',
    tech_3='Telegram Bot',
    motivation='Help people find dream jobs faster',
    demo_link='https://wa.me/50766623757'
)
```

## 🌍 Multi-Language Support

LinkedIn CMO supports English and Spanish:

```python
# English post
cmo = LinkedInCMO(language='en')

# Spanish post
cmo = LinkedInCMO(language='es')

# Or specify per post
post = cmo.generate_linkedin_post('open_to_work', language='es')
```

## 📅 Schedule Weekly Posts

Schedule a week's worth of content:

```python
schedule = [
    {
        'day': 'Monday',
        'post_type': 'open_to_work',
        'variables': {
            'role': 'Founding Engineer',
            'demo_link': 'https://wa.me/50766623757'
        }
    },
    {
        'day': 'Wednesday',
        'post_type': 'insight',
        'variables': {
            'project': 'VibeJobHunter',
            'main_insight': 'Automation saves 10+ hours per week'
        }
    },
    {
        'day': 'Friday',
        'post_type': 'demo_share',
        'variables': {
            'project_name': 'VibeJobHunter',
            'demo_link': 'https://wa.me/50766623757'
        }
    }
]

await cmo.schedule_weekly_posts(schedule)
```

## 🔗 Integration with Autonomous Orchestrator (Optional)

To add LinkedIn posting to your autonomous workflow, update `src/autonomous/orchestrator.py`:

```python
# In __init__ method, add:
from ..notifications import LinkedInCMO
self.linkedin_cmo = LinkedInCMO()

# In run_autonomous_cycle or start_autonomous_mode, add:
# Post weekly updates
if datetime.now().weekday() == 0:  # Monday
    await self.linkedin_cmo.post_open_to_work(
        role='Founding Engineer',
        demo_link='https://wa.me/50766623757'
    )
```

## 📊 Get Statistics

```python
stats = cmo.get_stats()
print(f"Posts sent: {stats['posts_sent']}")
print(f"Enabled: {stats['enabled']}")
print(f"Last post: {stats['last_post_date']}")
```

## 🛡️ Safety Features

- ✅ Graceful degradation (works even without webhook configured)
- ✅ Content preview before posting
- ✅ No impact on existing job search functionality
- ✅ Separate module - easy to enable/disable
- ✅ Multi-language support built-in

## 🧪 Testing

To test without sending to Make.com:

```python
from src.notifications import LinkedInCMO

# Initialize without webhook
cmo = LinkedInCMO()

# Generate and preview (doesn't send)
preview = cmo.preview_post('open_to_work', language='en')
print(preview)

# Check stats
print(cmo.get_stats())
```

## ❓ Troubleshooting

### Posts Not Sending
1. Check webhook URL is set in `.env`
2. Verify Make.com scenario is active
3. Check logs for error messages

### Wrong Language
```python
# Explicitly set language
cmo = LinkedInCMO(language='en')  # or 'es'
```

### Customize Templates
Edit `src/notifications/linkedin_cmo.py` and modify the `self.templates` dictionary.

## 🎯 Best Practices

1. **Preview First**: Always preview posts before sending
2. **Customize Variables**: Personalize with your own achievements
3. **Schedule Wisely**: Don't post too frequently (2-3x per week is good)
4. **Mix Content**: Use different post types for variety
5. **Track Performance**: Monitor stats to see what works

## 🔄 Restore Previous Version

If you need to go back to the version before LinkedIn CMO:

```bash
# See all backups
git branch -a | grep backup

# Restore backup
git checkout backup-before-linkedin-cmo-20251122-201510

# Or use the tag
git tag -l | grep backup
git checkout backup-20251122-201510
```

## ✅ Verification Checklist

- [x] LinkedIn CMO file created
- [x] Import added to notifications module
- [x] Webhook URL added to .env.example
- [x] No syntax errors
- [x] No linter errors
- [x] Existing job search untouched
- [x] Telegram notifications untouched
- [x] CLI still works
- [x] All imports work

## 📞 Need Help?

The LinkedIn CMO is completely separate from job search functionality. If something breaks:

1. Check git status: `git status`
2. See what changed: `git diff`
3. Restore if needed: `git checkout backup-before-linkedin-cmo-20251122-201510`

**Remember**: The LinkedIn CMO is an ADD-ON. It doesn't modify any existing functionality!
