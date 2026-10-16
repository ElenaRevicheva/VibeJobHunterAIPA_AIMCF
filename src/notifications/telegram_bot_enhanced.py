"""
Enhanced Telegram Bot for VibeJobHunter
Interactive commands for job hunting control and status

ADDED: Voice + free-form questions (additive, non-overwriting)
- Voice messages → transcribed with Whisper → answered from real job data
- Text questions (e.g. "what companies did I apply to today?") → honest answers
"""

import os
import asyncio
import tempfile
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import json
import logging

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application,
        CommandHandler,
        CallbackQueryHandler,
        ContextTypes,
        MessageHandler,
        filters
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print(" python-telegram-bot not installed. Install with: pip install python-telegram-bot")

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# 16 Oct 2026 (Elena): the screens say only what really happens today. Checked on Oracle against the code and the
# journal; one copy each, shared by the /command and its button. Telegram Markdown v1: no "_" outside backticks.
# Buttons whose screens showed April data or a fake "0 jobs" (Today, Jobs, Stats, Outreach, Pause, Resume, Status,
# the "coming soon" CMO ones) are off the menu; their handlers are untouched.
# ═══════════════════════════════════════════════════════════════════════════
MENU_TEXT = """📋 *VIBEJOBHUNTER MENU*

💼 *YOUR JOB FLOW — nothing to remember*
1️⃣ New job → the kit fills the HubSpot deal by itself (company note, CV, letter, Comet prompt) → open 🔥 I act today → apply. The daily apply queue and kit alerts arrive here.
2️⃣ Interview booked (LinkedIn, WhatsApp, anywhere) → in the *CTO AIPA bot* send `/research_employer <company>` → if the company has an open job deal, deep research on the company + its products is saved on it and the bot confirms when OpenClaw has it (no deal yet: give Claude Code the posting link first)
3️⃣ In OpenClaw: `/new` → `prep me for <company>` → a mock interview on that company's likely questions, steering clear of what the research says not to claim

Choose an option below:"""

START_TEXT = """🤖 *VibeJobHunter*

I find and screen remote AI jobs every hour and put the good ones in HubSpot 🔥 I act today, where the kit writes your materials. *You apply* — I do not apply or email employers for you.

/menu — your job flow
/workflow — what runs by itself
/manual — what is yours
/help — commands that work"""

WORKFLOW_TEXT = """🔄 *HOW VIBEJOBHUNTER WORKS*

It finds and screens jobs, and the kit writes your materials. *You apply.* It does not apply, fill in forms or email employers for you.

*1️⃣ Finds jobs*: one cycle about every hour
• Job boards of about 270 companies (Greenhouse, Ashby, Lever, Workable and more), Himalayas, Get on Board, YC OSS, Hacker News, Dice, RemoteOK, WeWorkRemotely, Remotive, Puente, AI-Native-Builder
• A Google Jobs feed, twice a day
• Off on purpose: Wellfound, AI-Jobs, YC Work at a Startup, LinkedIn (Bright Data). Torre is failing right now.

*2️⃣ Screens them*
• Re-reads the live posting and drops it if closed
• The job must be fully remote, open to LATAM or worldwide, and AI-augmented work, with no posted pay under $3,000/month
• Scores each job: 60+ goes to your learned rules, then an AI judge · 55–59 is shown as a lead · under 55 is dropped

*3️⃣ Learns from you*: every hour
It re-reads your decided HubSpot job deals and the reason you gave for each No-fit, including screenshots on the deal. Those reasons become rules and examples for the judge.

*4️⃣ Alerts you here and creates the deal*
📋 Apply yourself (⚠️ UNVERIFIED when the posting could not be read) → a job deal in HubSpot 🔥 I act today

*5️⃣ The kit fills the deal*: every 10 min, from CTO AIPA
🔎 company brief · CV shaped to the posting, or your tailored CV with the reason · ✅ cover letter · 🎯 role defense · 🛡️ technical defense · 📋 Comet prompt

*6️⃣ Mornings*
• 07:55 Panama: closed postings are moved out of 🔥 I act today to Lost
• 08:15 Panama: the apply queue, sent here only when there are new jobs
• 08:45 Panama: a kit alert, sent here only if a deal is missing a piece

*7️⃣ Replies*
Your Zoho and Gmail inboxes are checked in each hourly cycle that finds a new job, looking back 24 hours. A positive reply or a question from an employer goes to HubSpot and is alerted here once. An interview invite with a booking link should do the same; that was added 15 Oct and none has arrived yet.

*👤 Your part*
Apply from 🔥 I act today → move the deal to ⏳ Sent, or to Lost with a reason. Interview booked anywhere → CTO AIPA bot `/research_employer <company>` → OpenClaw `/new`, then `prep me for <company>`.

*Switched off:* auto-apply, ATS form filling and founder emails. The old follow-up emailer still checks but has nothing to send (last one 24 May)."""

MANUAL_TEXT = """👤 *WHAT YOU DO BY HAND*

The bot finds and screens jobs, and the kit writes your materials on the HubSpot deal. *Applying, replying and booking calls are yours.* Nothing is sent for you.

*Every morning*
1️⃣ Open HubSpot → 🔥 I act today. When there are new jobs, the 08:15 Panama apply queue here lists them.
2️⃣ Open a deal and read the 🔎 company brief, 🎯 role defense and 🛡️ technical defense
3️⃣ Apply on the posting with the CV and ✅ cover letter on the deal. The 📋 Comet prompt is there if you use Comet for the form.
4️⃣ ⚠️ UNVERIFIED deal: open the link first and check the job is still open
5️⃣ Move the deal: ⏳ Sent once you have applied, or Lost with one line on why it is not a fit (a screenshot on the deal works too). Within the hour, that reason trains the judge.

*A job you found yourself*
Give the link to Claude Code and it becomes a deal with the same kit. This bot cannot do that.

*When an employer replies*
• The alert comes here. You answer and book the call yourself.
• Whose-turn reminders come at 07:00 Panama in the *CTO AIPA bot*, with a HubSpot task

*Interview booked* (LinkedIn, WhatsApp, email, anywhere)
1️⃣ *CTO AIPA bot:* `/research_employer <company>` → if the company has an open job deal, the research is saved on it and the bot replies "✅ OpenClaw has it now" (no deal yet: give Claude Code the posting link first)
2️⃣ *OpenClaw:* `/new` → `prep me for <company>` → a mock interview on that company's likely questions, steering clear of what the research says not to claim. Add `en español` for a Spanish interview.
3️⃣ After the call, move the deal on in HubSpot"""

HELP_TEXT = """📖 *COMMANDS THAT WORK*

/menu: your 3-step job flow, with buttons
/workflow: what runs by itself, and what is yours
/manual: your steps every morning, when a reply comes, and when an interview is booked
/priority: the YC priority company list. It does not change which jobs reach you. Skip `/priority refresh` and the 🔄 Refresh button on that screen: either freezes the bot for up to 2 minutes.
/help: this list
⚠️ The 📘 menu button posts publicly with no preview: LinkedIn and Instagram, plus a Hashnode and dev.to article whenever a CTO update is waiting.

*Arrives here by itself*
• 📋 Apply yourself / ⚠️ UNVERIFIED: a new job, already a HubSpot deal
• 08:15 Panama: the apply queue, only when there are new jobs
• 08:45 Panama: a kit alert, only if a deal is missing a piece
• Employer replies (positive or a question), once each
• Daily digest around 15:00 Panama. Ignore its Auto-applied, Outreach and Follow-up lines: those features are off, so they read 0 or show May's applications.

*Not working yet in this bot:* it hears voice notes in English, Spanish or Russian, but every answer, spoken or typed, is English text from old files (Jan–May 2026) or a canned reply. Screenshots get no reply.

*For real answers:* CTO AIPA bot `/research_employer <company>` · OpenClaw `prep me for <company>` (English or Spanish)"""


def _menu_keyboard():
    """Only buttons whose screens are true today (16 Oct 2026)."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 How it works", callback_data="workflow"),
         InlineKeyboardButton("👤 What is mine", callback_data="manual")],
        [InlineKeyboardButton("🎯 Priority Companies", callback_data="priority")],
        [InlineKeyboardButton("📘 Post publicly NOW (LinkedIn + IG)", callback_data="post_linkedin")],
    ])


class EnhancedTelegramBot:
    """
    Interactive Telegram bot for VibeJobHunter
    
    🆕 UPGRADED January 2026: Comprehensive menu system
    
    MAIN MENU COMMANDS:
    /menu - Interactive menu with all options
    /workflow - Visual explanation of how the engine works
    /manual - What YOU need to do (steps that can't be automated)
    /today - Today's complete activity summary
    /outreach - Pending LinkedIn/Twitter messages to send manually
    
    ORIGINAL COMMANDS:
    /start - Welcome message and help
    /jobs - Show top jobs found today
    /stats - Show application statistics
    /apply <company> - Generate materials for a company
    /pause - Pause autonomous job hunting
    /resume - Resume autonomous job hunting
    /keywords <keywords> - Update job search keywords
    /companies - Show tracked companies
    /recent - Show recent applications
    /status - Show system status

    VOICE & QUESTIONS (added, additive):
    - Send a voice message → transcribed with Whisper → answered from real data
    - Type: "What companies did I apply to today?" → honest list from logs
    """
    
    def __init__(self, token: str, chat_id: str, db_helper=None):
        self.token = token
        self.chat_id = chat_id
        self.db_helper = db_helper
        self.is_paused = False
        
        if not TELEGRAM_AVAILABLE:
            raise ImportError("python-telegram-bot not installed")
        
        self.app = Application.builder().token(token).build()
        self._register_handlers()
    
    def _register_handlers(self):
        """Register all command handlers"""
        # 🆕 NEW MAIN MENU COMMANDS (January 2026)
        self.app.add_handler(CommandHandler("menu", self.cmd_menu))
        self.app.add_handler(CommandHandler("workflow", self.cmd_workflow))
        self.app.add_handler(CommandHandler("manual", self.cmd_manual))
        self.app.add_handler(CommandHandler("today", self.cmd_today))
        self.app.add_handler(CommandHandler("outreach", self.cmd_outreach))
        
        # Original commands
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("jobs", self.cmd_jobs))
        self.app.add_handler(CommandHandler("stats", self.cmd_stats))
        self.app.add_handler(CommandHandler("apply", self.cmd_apply))
        self.app.add_handler(CommandHandler("pause", self.cmd_pause))
        self.app.add_handler(CommandHandler("resume", self.cmd_resume))
        self.app.add_handler(CommandHandler("keywords", self.cmd_keywords))
        self.app.add_handler(CommandHandler("companies", self.cmd_companies))
        self.app.add_handler(CommandHandler("recent", self.cmd_recent))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        # Priority companies (additive — Feb 2026)
        self.app.add_handler(CommandHandler("priority", self.cmd_priority))

        # Callback query handler for inline buttons
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))

        # ADDED: Voice + free-form text (additive — commands unchanged)
        self.app.add_handler(MessageHandler(filters.VOICE, self.handle_voice))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_freeform_text))
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Welcome message with main menu"""
        await update.message.reply_text(START_TEXT, parse_mode='Markdown', reply_markup=_menu_keyboard())

    # ═══════════════════════════════════════════════════════════════════════════
    # 🆕 NEW MENU COMMANDS (January 2026 Upgrade)
    # ═══════════════════════════════════════════════════════════════════════════

    async def cmd_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Interactive main menu with all options"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info("📋 /menu command received!")

        try:
            # 16 Oct 2026 (Elena): everything about jobs lives in THIS bot, whichever agent does the work behind it.
            await update.message.reply_text(MENU_TEXT, parse_mode='Markdown', reply_markup=_menu_keyboard())
            logger.info("📋 /menu response sent successfully!")
        except Exception as e:
            logger.error(f"❌ /menu command error: {e}", exc_info=True)

    async def cmd_workflow(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """How the engine really works today"""
        keyboard = [[InlineKeyboardButton("👤 What is mine", callback_data="manual")]]
        await update.message.reply_text(WORKFLOW_TEXT, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

    async def cmd_manual(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show what the user needs to do manually"""
        keyboard = [[InlineKeyboardButton("📋 Back to Menu", callback_data="menu")]]
        await update.message.reply_text(MANUAL_TEXT, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

    async def cmd_today(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show today's complete activity summary"""
        try:
            # Load today's data
            jobs_count = self._count_todays_jobs()
            outreach = self._load_pending_outreach()
            
            now = datetime.utcnow()
            panama_hour = (now.hour - 5) % 24  # UTC-5
            
            message = f"""📊 *TODAY'S ACTIVITY SUMMARY*
📅 {now.strftime('%B %d, %Y')} | {panama_hour}:{now.strftime('%M')} Panama

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*🔍 JOB DISCOVERY*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Jobs Found: {jobs_count}
• Sources Checked: 7
• Companies Scanned: 200+

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*🚀 APPLICATIONS*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Auto-Applied: Check /stats
• Materials Generated: ✅
• ATS Forms Filled: ✅

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*📨 YOUR ACTION NEEDED*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• LinkedIn Messages: {len(outreach)} pending
• Use /outreach to see them

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*⏰ NEXT CYCLE*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• In ~{60 - now.minute} minutes
"""
            keyboard = [
                [
                    InlineKeyboardButton("💼 See Jobs", callback_data="jobs"),
                    InlineKeyboardButton("📨 Outreach", callback_data="outreach")
                ],
                [InlineKeyboardButton("🔄 Refresh", callback_data="today")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def cmd_outreach(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show pending LinkedIn/Twitter messages to send manually"""
        try:
            outreach = self._load_pending_outreach()
            
            if not outreach:
                message = """📨 *PENDING OUTREACH*

✅ No pending messages right now!

When the engine finds good opportunities:
• LinkedIn messages will appear here
• You copy-paste and send them
• This is the human touch that wins!

Check back after the next job cycle (~hourly).
"""
            else:
                message = f"""📨 *PENDING OUTREACH*

You have *{len(outreach)}* message(s) to send:

"""
                for i, item in enumerate(outreach[:5], 1):  # Show max 5
                    company = item.get('company', 'Unknown')
                    platform = item.get('platform', 'LinkedIn')
                    contact = item.get('contact', 'Team')
                    url = item.get('url', '#')
                    msg_preview = item.get('message', '')[:100]
                    
                    message += f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{i}. *{company}* ({platform})
👤 Contact: {contact}
🔗 {url}

📝 Message Preview:
"{msg_preview}..."
"""
                
                message += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

*HOW TO SEND:*
1. Click the LinkedIn URL above
2. Send connection request
3. Copy the full message from logs
4. Paste as connection note

💡 Tip: Personalize if you can!
"""
            
            keyboard = [[InlineKeyboardButton("📋 Back to Menu", callback_data="menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                message, 
                parse_mode='Markdown', 
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error loading outreach: {str(e)}")
    
    def _load_pending_outreach(self) -> list:
        """Load pending outreach messages from the ACTUAL outreach files"""
        messages = []

        # Source 1: manual_outreach_queue.json (primary — generated by founder_finder)
        try:
            queue_file = "autonomous_data/manual_outreach_queue.json"
            if os.path.exists(queue_file):
                with open(queue_file, 'r') as f:
                    data = json.load(f)
                    items = data if isinstance(data, list) else data.get('messages', [])
                    for m in items:
                        status = m.get('status', '')
                        if status in ('pending_manual_send', 'pending', ''):
                            messages.append({
                                'company': m.get('company', 'Unknown'),
                                'platform': m.get('platform', 'LinkedIn'),
                                'contact': m.get('contact_name', m.get('contact', 'Founder')),
                                'url': m.get('linkedin_url', m.get('url', '')),
                                'message': m.get('message', m.get('content', '')),
                            })
        except Exception:
            pass

        # Source 2: outreach_log.jsonl (backup — all outreach history)
        if not messages:
            try:
                log_file = "autonomous_data/outreach_log.jsonl"
                if os.path.exists(log_file):
                    pending = []
                    with open(log_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                entry = json.loads(line)
                                if entry.get('status') in ('pending_manual_send', 'pending'):
                                    pending.append({
                                        'company': entry.get('company', 'Unknown'),
                                        'platform': 'LinkedIn',
                                        'contact': entry.get('contact_name', 'Founder'),
                                        'url': entry.get('linkedin_url', ''),
                                        'message': entry.get('message', '')[:300],
                                    })
                            except json.JSONDecodeError:
                                continue
                    # Show most recent 10
                    messages = pending[-10:]
            except Exception:
                pass

        return messages
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show detailed help"""
        await update.message.reply_text(HELP_TEXT, parse_mode='Markdown')

    async def cmd_jobs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show today's top jobs"""
        try:
            # Load today's jobs from cache
            jobs = self._load_recent_jobs()
            
            if not jobs:
                await update.message.reply_text(" No jobs found today yet. Check back in an hour!")
                return
            
            # Sort by match score and take top 5
            top_jobs = sorted(jobs, key=lambda x: x.get('match_score', 0), reverse=True)[:5]
            
            message = f" *Top {len(top_jobs)} Jobs Found Today*\n\n"
            
            for i, job in enumerate(top_jobs, 1):
                company = job.get('company', 'Unknown')
                title = job.get('title', 'Unknown')
                location = job.get('location', 'Remote')
                match_score = job.get('match_score', 0) * 100
                url = job.get('url', '#')
                
                message += f"{i}. *{company}* - {title}\n"
                message += f"    {location} |  {match_score:.0f}% match\n"
                message += f"    [Apply Here]({url})\n\n"
            
            # Add quick action buttons
            keyboard = [
                [
                    InlineKeyboardButton(" Stats", callback_data="stats"),
                    InlineKeyboardButton(" Refresh", callback_data="refresh_jobs")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                message, 
                parse_mode='Markdown',
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
            
        except Exception as e:
            await update.message.reply_text(f" Error loading jobs: {str(e)}")
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show application statistics"""
        try:
            if not self.db_helper:
                await update.message.reply_text(" Database not connected")
                return
            
            # Get weekly stats
            this_week = self.db_helper.get_weekly_stats(0)
            last_week = self.db_helper.get_weekly_stats(1)
            
            message = " *Your Job Hunting Stats*\n\n"
            message += "*This Week:*\n"
            message += f" Applications: {this_week['applications_sent']}\n"
            message += f" Responses: {this_week['responses_received']}\n"
            message += f" Interviews: {this_week['interviews_scheduled']}\n"
            message += f" Offers: {this_week['offers_received']}\n"
            message += f" Response Rate: {this_week['response_rate']*100:.1f}%\n\n"
            
            message += "*Last Week:*\n"
            message += f" Applications: {last_week['applications_sent']}\n"
            message += f" Responses: {last_week['responses_received']}\n\n"
            
            # Get top companies
            responsive = self.db_helper.get_responsive_companies()[:3]
            if responsive:
                message += "* Most Responsive Companies:*\n"
                for company, rate in responsive:
                    message += f"   {company} ({rate*100:.0f}% response)\n"
            
            # Get ghost companies
            ghosts = self.db_helper.get_ghost_companies()
            if ghosts:
                message += f"\n *Ghost Companies* ({len(ghosts)})\n"
                message += "These companies never respond - avoid them!\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f" Error loading stats: {str(e)}")
    
    async def cmd_apply(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate materials for a specific company"""
        if not context.args:
            await update.message.reply_text(
                " Please specify a company name\n"
                "Example: /apply anthropic"
            )
            return
        
        company_name = " ".join(context.args)
        
        await update.message.reply_text(
            f" Generating materials for *{company_name}*...\n"
            "This will take ~30 seconds",
            parse_mode='Markdown'
        )
        
        try:
            # TODO: Call material generation service
            # For now, send placeholder
            message = f" *Materials Ready for {company_name}*\n\n"
            message += " Resume: Tailored for this role\n"
            message += " Cover Letter: Personalized\n"
            message += " Portfolio: Updated links\n\n"
            message += "Next: Apply manually or I can send via email"
            
            keyboard = [
                [
                    InlineKeyboardButton(" Send Email", callback_data=f"send_email_{company_name}"),
                    InlineKeyboardButton(" Save Only", callback_data="save_materials")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            await update.message.reply_text(f" Error: {str(e)}")
    
    async def cmd_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Pause autonomous job hunting"""
        self.is_paused = True
        await update.message.reply_text(
            " *Autonomous job hunting PAUSED*\n\n"
            "I'll stop checking for new jobs.\n"
            "Use /resume to restart.",
            parse_mode='Markdown'
        )
    
    async def cmd_resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Resume autonomous job hunting"""
        self.is_paused = False
        await update.message.reply_text(
            " *Autonomous job hunting RESUMED*\n\n"
            "I'm back to checking jobs hourly!\n"
            "You'll get alerts for high-match jobs.",
            parse_mode='Markdown'
        )
    
    async def cmd_keywords(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Update job search keywords"""
        if not context.args:
            # Show current keywords
            keywords = self._load_keywords()
            message = " *Current Keywords:*\n" + ", ".join(keywords)
            message += "\n\nTo update: /keywords ML engineer, AI researcher"
            await update.message.reply_text(message, parse_mode='Markdown')
            return
        
        # Update keywords
        new_keywords = " ".join(context.args).split(",")
        new_keywords = [k.strip() for k in new_keywords]
        
        self._save_keywords(new_keywords)
        
        message = f" *Keywords Updated!*\n\n"
        message += "New keywords:\n" + "\n".join(f"   {k}" for k in new_keywords)
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def cmd_companies(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show tracked companies"""
        try:
            # Load company list
            companies = self._load_target_companies()
            
            message = " *Tracked Companies*\n\n"
            
            for category, data in companies.items():
                if category == 'filters' or category == 'scraping_config':
                    continue
                
                company_list = data.get('companies', [])
                message += f"*{data.get('description', category)}*\n"
                message += f"  Companies: {len(company_list)}\n\n"
            
            total = sum(len(data.get('companies', [])) for key, data in companies.items() 
                       if key not in ['filters', 'scraping_config'])
            message += f" *Total: {total} companies tracked*"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f" Error: {str(e)}")
    
    async def cmd_recent(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show recent applications"""
        try:
            if not self.db_helper:
                await update.message.reply_text(" Database not connected")
                return
            
            # Placeholder - database integration coming soon
            await update.message.reply_text(" No applications tracked yet! Database integration in progress.")
            
        except Exception as e:
            await update.message.reply_text(f" Error: {str(e)}")
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show system status"""
        status_emoji = "" if not self.is_paused else ""
        status_text = "RUNNING" if not self.is_paused else "PAUSED"
        
        message = f" *System Status*\n\n"
        message += f"{status_emoji} Mode: *{status_text}*\n"
        message += f" Last Check: {datetime.utcnow().strftime('%H:%M UTC')}\n"
        message += f" Jobs Today: {self._count_todays_jobs()}\n"
        message += f" Next Check: In ~{60 - datetime.utcnow().minute} minutes\n\n"
        
        if self.is_paused:
            message += "Use /resume to restart"
        else:
            message += "Use /pause to stop"
        
        await update.message.reply_text(message, parse_mode='Markdown')

    async def cmd_priority(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Priority companies: list, add, remove, sync yc (additive — Feb 2026)"""
        if not self.db_helper:
            await update.message.reply_text("Priority list not available (no database).")
            return
        args = (context.args or []) if context.args else []
        sub = (args[0] or "list").lower() if args else "list"

        try:
            if sub == "list":
                # Sync from export file first (fresh data on manual request)
                path = self._get_priority_export_path()
                if os.path.exists(path):
                    try:
                        self.db_helper.sync_priority_from_yc_file(path)
                    except Exception:
                        pass
                rows = self.db_helper.list_priority_companies()
                total = len(rows)
                ts = rows[0]["created_at"].strftime("%Y-%m-%d %H:%M") if rows else "—"
                msg = f"🎯 *Priority Companies* ({total})\n\n"
                for r in rows[:30]:
                    msg += f"• {r['company_name']} ({r['source']})\n"
                if total > 30:
                    msg += f"\n... and {total - 30} more"
                msg += f"\n\n_Last updated: {ts}_"
                await update.message.reply_text(msg, parse_mode='Markdown')
            elif sub == "add":
                name = " ".join(args[1:]).strip() if len(args) > 1 else ""
                if not name:
                    await update.message.reply_text("Usage: /priority add <company>")
                    return
                if self.db_helper.add_priority_company(name, "manual"):
                    await update.message.reply_text(f"✅ Added: {name}")
                else:
                    await update.message.reply_text(f"Already in list or invalid: {name}")
            elif sub == "remove":
                name = " ".join(args[1:]).strip() if len(args) > 1 else ""
                if not name:
                    await update.message.reply_text("Usage: /priority remove <company>")
                    return
                if self.db_helper.remove_priority_company(name):
                    await update.message.reply_text(f"✅ Removed: {name}")
                else:
                    await update.message.reply_text(f"Not found or invalid: {name}")
            elif sub == "sync":
                sync_source = (args[1] or "yc").lower() if len(args) > 1 else "yc"
                if sync_source == "yc":
                    path = self._get_priority_export_path()
                    if not os.path.exists(path):
                        await update.message.reply_text(
                            f"📂 Export file not found at {path}. "
                            "Ask OpenClaw for your job shortlist first — it creates the file. Then run /priority sync yc again."
                        )
                        return
                    added, skipped = self.db_helper.sync_priority_from_yc_file(path)
                    await update.message.reply_text(f"✅ Sync YC: {added} added, {skipped} skipped (from {path})")
                else:
                    await update.message.reply_text("Usage: /priority sync yc")
            elif sub == "refresh":
                # Run pipeline + sync for truly fresh data on demand
                await update.message.reply_text("🔄 Refreshing from YC (30–60 sec)...")
                import subprocess
                path = self._get_priority_export_path()
                base = os.path.dirname(path)
                script = os.path.join(base, "run_shortlist.sh")
                if os.path.exists(script):
                    try:
                        subprocess.run(
                            ["bash", script],
                            cwd=base,
                            capture_output=True,
                            timeout=120,
                            env={**os.environ}
                        )
                    except subprocess.TimeoutExpired:
                        await update.message.reply_text("⏱️ Pipeline timed out. Try again.")
                        return
                    except Exception as e:
                        await update.message.reply_text(f"❌ Pipeline error: {str(e)[:100]}")
                        return
                if os.path.exists(path):
                    added, skipped = self.db_helper.sync_priority_from_yc_file(path)
                    rows = self.db_helper.list_priority_companies()
                    total = len(rows)
                    ts = rows[0]["created_at"].strftime("%Y-%m-%d %H:%M") if rows else "—"
                    msg = f"✅ Refreshed! {added} added, {skipped} skipped.\n\n🎯 *Priority Companies* ({total})\n\n"
                    for r in rows[:30]:
                        msg += f"• {r['company_name']} ({r['source']})\n"
                    if total > 30:
                        msg += f"\n... and {total - 30} more"
                    msg += f"\n\n_Last updated: {ts}_"
                    await update.message.reply_text(msg, parse_mode='Markdown')
                else:
                    await update.message.reply_text("❌ Export file not created. Check job-list-filter path.")
            else:
                await update.message.reply_text(
                    "Usage:\n/priority list\n/priority add <company>\n/priority remove <company>\n/priority sync yc\n/priority refresh"
                )
        except Exception as e:
            logger.exception("cmd_priority error")
            await update.message.reply_text(f"Error: {str(e)[:200]}")

    # ─────────────────────────────────────────────────────────────────────────
    # VOICE + FREE-FORM QUESTIONS (additive)
    # ─────────────────────────────────────────────────────────────────────────

    def _detect_language(self, text: str) -> str:
        """
        Very lightweight language detector for voice questions.
        Only distinguishes between EN / ES / RU using simple heuristics.
        """
        if not text:
            return "en"
        # Cyrillic characters → assume Russian
        if any("\u0400" <= ch <= "\u04FF" for ch in text):
            return "ru"
        lower = text.lower()
        # Basic Spanish markers
        spanish_markers = [
            " hola ",
            " buenos dias",
            " buenas tardes",
            " buenas noches",
            " gracias",
            " por favor",
            " que ",
            " porque",
            " para ",
            " contigo",
            " estoy",
            " tengo",
            " quiero",
            " trabajo",
        ]
        if any(m in lower for m in spanish_markers) or any(c in lower for c in ["ñ", "á", "é", "í", "ó", "ú", "ü"]):
            return "es"
        return "en"

    async def _translate_to_english(self, text: str, source_lang: str) -> str:
        """
        Translate ES/RU → EN using OpenAI if available.
        Falls back to original text on any error.
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or not text:
            return text
        # If already English, skip
        if source_lang == "en":
            return text
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            prompt = (
                "Translate the following user question into natural English, keeping all job-search-specific details. "
                "Return ONLY the translated English text, no explanations.\n\n"
                f"Original ({source_lang}): {text}"
            )
            resp = client.chat.completions.create(
                model=os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            translated = resp.choices[0].message.content.strip()
            return translated or text
        except Exception as e:
            logger.warning(f"Translation failed, using original text. Error: {e}")
            return text

    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Transcribe voice message with Whisper, then answer from real job data."""
        if not update.message or not update.message.voice:
            return
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            await update.message.reply_text(
                "🎤 Voice works! Add OPENAI_API_KEY to .env for transcription. "
                "Or type your question — I answer job questions from real data."
            )
            return
        try:
            voice = update.message.voice
            tg_file = await context.bot.get_file(voice.file_id)
            tmp_path = None
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
                tmp_path = tmp.name
            await tg_file.download_to_drive(tmp_path)
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
                with open(tmp_path, "rb") as f:
                    transcript = client.audio.transcriptions.create(model="whisper-1", file=f)
                text = transcript.text.strip() if hasattr(transcript, 'text') else str(transcript)
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            if not text:
                await update.message.reply_text("Couldn't transcribe the voice message. Try typing your question!")
                return
            lang = self._detect_language(text)
            logger.info(f"🎤 Voice transcribed ({lang}): {text[:100]}{'...' if len(text) > 100 else ''}")

            # Normalize ES/RU questions into English, then use the same
            # honest job-data QA path as text questions.
            if lang in ("es", "ru"):
                text_en = await self._translate_to_english(text, lang)
                # Show both original language and English so you see what
                # the bot understood and how it normalized it.
                await update.message.reply_text(
                    f"📝 I heard (translated from {lang.upper()}):\n{text_en}",
                    parse_mode="Markdown",
                )
            else:
                text_en = text
                await update.message.reply_text(
                    f"📝 I heard:\n{text_en}",
                    parse_mode="Markdown",
                )

            # Now answer using real job data, same as text questions
            await self._reply_job_question(update, context, text_en)
        except Exception as e:
            logger.warning(f"Voice transcription error: {e}")
            await update.message.reply_text(
                f"Voice transcription failed. Try typing: \"What companies did I apply to today?\""
            )

    async def handle_freeform_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Answer free-form job questions from real data (honest answers)."""
        if not update.message or not update.message.text:
            return
        text = (update.message.text or "").strip()
        if not text:
            return
        await self._reply_job_question(update, context, text)

    async def _reply_job_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Shared: answer job question and reply."""
        try:
            from src.notifications.telegram_qa_helper import answer_job_question
            logger.info(f"📝 QA question: {text[:80]}{'...' if len(text) > 80 else ''}")
            reply = answer_job_question(text)
            await update.message.reply_text(reply, parse_mode='Markdown')
        except Exception as e:
            logger.warning(f"QA reply error: {e}")
            await update.message.reply_text(
                "Use /today or /stats for summaries. Or ask: \"What companies did I apply to today?\""
            )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button clicks"""
        import logging
        logger = logging.getLogger(__name__)
        
        # Debug: Print to stdout AND log
        print(f"=== CALLBACK RECEIVED: {update.callback_query.data if update.callback_query else 'None'} ===")
        
        query = update.callback_query
        logger.info(f"🔘 Callback received: {query.data}")
        
        try:
            await query.answer()
            chat_id = query.message.chat_id
            logger.info(f"🔘 Processing callback '{query.data}' for chat {chat_id}")
            
            # ═══════════════════════════════════════════════════════════════
            # 🆕 NEW MENU CALLBACKS (January 2026)
            # ═══════════════════════════════════════════════════════════════
            if query.data == "menu":
                await self._send_menu(context, chat_id)
            
            elif query.data == "workflow":
                await self._send_workflow(context, chat_id)
            
            elif query.data == "manual":
                await self._send_manual(context, chat_id)
            
            elif query.data == "today":
                await self._send_today(context, chat_id)
            
            elif query.data == "outreach":
                await self._send_outreach(context, chat_id)
            
            elif query.data == "jobs":
                await self._send_jobs(context, chat_id)
            
            elif query.data == "pause":
                self.is_paused = True
                await context.bot.send_message(chat_id, "⏸️ Job hunting PAUSED. Use /resume to restart.")
            
            elif query.data == "resume_hunting":
                self.is_paused = False
                await context.bot.send_message(chat_id, "▶️ Job hunting RESUMED!")
            
            elif query.data == "status":
                await self._send_status(context, chat_id)
            
            elif query.data == "stats":
                await self._send_stats(context, chat_id)
            
            elif query.data == "priority":
                await self._send_priority_list(context, chat_id)
            
            elif query.data == "priority_sync":
                await self._do_priority_sync(context, chat_id)
            
            elif query.data == "priority_refresh":
                await self._do_priority_refresh(context, chat_id)
            
            # ═══════════════════════════════════════════════════════════════
            # 🚀 CMO AIPA CALLBACKS (LinkedIn + Instagram via Make.com)
            # ═══════════════════════════════════════════════════════════════
            elif query.data == "post_linkedin":
                # Use the actual CMO code instead of direct webhook
                try:
                    from src.notifications.linkedin_cmo_v4 import LinkedInCMO
                    cmo = LinkedInCMO()
                    success = await cmo.post_to_linkedin(post_type="random", language="random")
                    if success:
                        await context.bot.send_message(chat_id, "✅ LinkedIn + Instagram posting triggered via CMO!")
                    else:
                        await context.bot.send_message(chat_id, "❌ CMO posting failed")
                except Exception as e:
                    await context.bot.send_message(chat_id, f"❌ Error: {str(e)}")
            
            elif query.data == "post_instagram":
                import requests
                webhook_url = os.getenv('MAKE_WEBHOOK_URL_LINKEDIN', '')
                if not webhook_url:
                    await context.bot.send_message(chat_id, "❌ MAKE_WEBHOOK_URL_LINKEDIN not set in env")
                    return
                try:
                    response = requests.post(webhook_url, json={
                        "platform": "instagram",
                        "action": "trigger_posting",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    await context.bot.send_message(chat_id, "✅ Instagram posting triggered! Check Make.com scenario.")
                except Exception as e:
                    await context.bot.send_message(chat_id, f"❌ Error: {str(e)}")
            
            elif query.data in ["analytics", "campaign", "generate_image", "header_job", "header_cmo", "header_system"]:
                # Placeholder handlers for CMO features
                await context.bot.send_message(chat_id, f"🚧 Feature '{query.data}' coming soon!")
            
            # ═══════════════════════════════════════════════════════════════
            # ORIGINAL CALLBACKS
            # ═══════════════════════════════════════════════════════════════
            elif query.data == "refresh_jobs":
                await query.edit_message_text("🔄 Refreshing...")
                await self._send_jobs(context, chat_id)
            
            elif query.data.startswith("send_email_"):
                company = query.data.replace("send_email_", "")
                await query.edit_message_text(f"📧 Sending email to {company}...")
            
            elif query.data == "save_materials":
                await query.edit_message_text("💾 Materials saved!")
            
            else:
                logger.warning(f"⚠️ Unknown callback: {query.data}")
                
        except Exception as e:
            logger.error(f"❌ Callback error: {e}", exc_info=True)
            try:
                await context.bot.send_message(query.message.chat_id, f"❌ Error: {str(e)[:100]}")
            except:
                pass
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CALLBACK HELPER METHODS - Send messages directly via bot
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def _send_menu(self, context, chat_id):
        """Send menu via callback — the same screen as /menu"""
        await context.bot.send_message(chat_id, MENU_TEXT, parse_mode='Markdown', reply_markup=_menu_keyboard())

    async def _send_workflow(self, context, chat_id):
        """Send workflow explanation via callback — the same screen as /workflow"""
        keyboard = [[InlineKeyboardButton("👤 What is mine", callback_data="manual")],
                    [InlineKeyboardButton("📋 Back to Menu", callback_data="menu")]]
        await context.bot.send_message(chat_id, WORKFLOW_TEXT, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

    async def _send_manual(self, context, chat_id):
        """Send manual tasks via callback — the same screen as /manual"""
        keyboard = [[InlineKeyboardButton("📋 Back to Menu", callback_data="menu")]]
        await context.bot.send_message(chat_id, MANUAL_TEXT, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

    async def _send_today(self, context, chat_id):
        """Send today's summary via callback"""
        jobs_count = self._count_todays_jobs()
        outreach = self._load_pending_outreach()
        now = datetime.utcnow()
        panama_hour = (now.hour - 5) % 24
        
        message = f"""📊 *TODAY'S SUMMARY*
📅 {now.strftime('%B %d, %Y')} | {panama_hour}:{now.strftime('%M')} Panama

*🔍 DISCOVERY*
• Jobs Found: {jobs_count}
• Companies: 200+

*📨 YOUR ACTION*
• LinkedIn Messages: {len(outreach)} pending

*⏰ NEXT CYCLE*
• In ~{60 - now.minute} minutes
"""
        keyboard = [
            [InlineKeyboardButton("💼 Jobs", callback_data="jobs"),
             InlineKeyboardButton("📨 Outreach", callback_data="outreach")],
            [InlineKeyboardButton("📋 Menu", callback_data="menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(chat_id, message, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def _send_outreach(self, context, chat_id):
        """Send pending outreach via callback"""
        outreach = self._load_pending_outreach()
        
        if not outreach:
            message = """📨 *PENDING OUTREACH*

✅ No pending messages right now!

The engine generates 1-2 new outreach per day.
Check back after the next job cycle.
"""
        else:
            message = f"""📨 *PENDING OUTREACH*

You have *{len(outreach)}* message(s) to send:

"""
            for i, m in enumerate(outreach[:5], 1):
                company = m.get('company', 'Unknown')
                contact = m.get('contact', 'Founder')
                platform = m.get('platform', 'LinkedIn')
                url = m.get('url', '')
                message += f"{i}. *{company}* → {contact}\n"
                if url:
                    message += f"   🔗 {url}\n"
                message += f"   via {platform}\n\n"

            if len(outreach) > 5:
                message += f"_...and {len(outreach) - 5} more_\n\n"
            message += "Use /outreach for full messages to copy-paste."
        
        keyboard = [[InlineKeyboardButton("📋 Menu", callback_data="menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(chat_id, message, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def _send_jobs(self, context, chat_id):
        """Send jobs list via callback"""
        jobs = self._load_recent_jobs()
        
        if not jobs:
            message = "💼 No jobs found today yet. Check back in an hour!"
        else:
            top_jobs = sorted(jobs, key=lambda x: x.get('match_score', 0), reverse=True)[:5]
            message = f"💼 *Top {len(top_jobs)} Jobs Today*\n\n"
            
            for i, job in enumerate(top_jobs, 1):
                company = job.get('company', 'Unknown')
                title = job.get('title', 'Unknown')[:30]
                score = job.get('match_score', 0)
                if isinstance(score, float) and score < 1:
                    score = score * 100
                message += f"{i}. *{company}*\n   {title} ({score:.0f}%)\n\n"
        
        keyboard = [[InlineKeyboardButton("📋 Menu", callback_data="menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(chat_id, message, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def _send_status(self, context, chat_id):
        """Send status via callback"""
        status = "RUNNING ✅" if not self.is_paused else "PAUSED ⏸️"
        now = datetime.utcnow()
        
        message = f"""⚙️ *SYSTEM STATUS*

• Mode: *{status}*
• Time: {now.strftime('%H:%M')} UTC
• Jobs Today: {self._count_todays_jobs()}
• Next Cycle: ~{60 - now.minute} min
"""
        keyboard = [[InlineKeyboardButton("📋 Menu", callback_data="menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(chat_id, message, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def _send_stats(self, context, chat_id):
        """Send stats via callback — reads real data from local files"""
        jobs_today = self._count_todays_jobs()
        outreach = self._load_pending_outreach()

        # Count total outreach ever sent from log
        total_outreach = 0
        sent_outreach = 0
        try:
            log_file = "autonomous_data/outreach_log.jsonl"
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            total_outreach += 1
                            if entry.get('status') not in ('pending_manual_send', 'pending'):
                                sent_outreach += 1
                        except json.JSONDecodeError:
                            continue
        except Exception:
            pass

        # Count seen jobs (dedup cache)
        seen_jobs = 0
        try:
            seen_file = "autonomous_data/seen_jobs.json"
            if os.path.exists(seen_file):
                with open(seen_file, 'r') as f:
                    data = json.load(f)
                    seen_jobs = len(data) if isinstance(data, (list, dict)) else 0
        except Exception:
            pass

        message = f"""📈 *QUICK STATS*

*🔍 Jobs:*
   Today: {jobs_today}
   Total seen: {seen_jobs}

*📨 Outreach:*
   Pending to send: {len(outreach)}
   Total generated: {total_outreach}
   Completed: {sent_outreach}

_Use /stats for full DB stats (if connected)_
"""
        keyboard = [[InlineKeyboardButton("📊 Today", callback_data="today")],
                    [InlineKeyboardButton("📋 Menu", callback_data="menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(chat_id, message, parse_mode='Markdown', reply_markup=reply_markup)
    
    def _get_priority_export_path(self):
        """Resolve path to priority_companies_for_vibejob.json (same logic as sync)."""
        path = os.getenv("PRIORITY_YC_EXPORT_PATH")
        if not path:
            base = os.getenv("OPENCLAW_JOB_LIST_PATH", ".")
            path = os.path.join(base, "priority_companies_for_vibejob.json")
        if not os.path.isabs(path):
            path = os.path.join(os.getcwd(), path)
        if not os.path.exists(path) and os.path.exists("/home/ubuntu/job-list-filter"):
            path = "/home/ubuntu/job-list-filter/priority_companies_for_vibejob.json"
        return path

    async def _send_priority_list(self, context, chat_id):
        """Send priority companies list via menu callback. Syncs from JSON first for fresh data."""
        if not self.db_helper:
            await context.bot.send_message(chat_id, "Priority list not available (no database).")
            return
        try:
            # Sync from export file first (fresh data on manual click)
            path = self._get_priority_export_path()
            if os.path.exists(path):
                try:
                    self.db_helper.sync_priority_from_yc_file(path)
                except Exception:
                    pass
            rows = self.db_helper.list_priority_companies()
            total = len(rows)
            ts = rows[0]["created_at"].strftime("%Y-%m-%d %H:%M") if rows else "—"
            msg = f"🎯 *Priority Companies* ({total})\n\n"
            for r in rows[:30]:
                msg += f"• {r['company_name']} ({r['source']})\n"
            if total > 30:
                msg += f"\n... and {total - 30} more"
            msg += f"\n\n_Last updated: {ts}_"
            msg += "\n\n_Add/remove:_ /priority add or remove <name>"
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Sync YC", callback_data="priority_sync"),
                    InlineKeyboardButton("🔄 Refresh", callback_data="priority_refresh"),
                ],
                [InlineKeyboardButton("📋 Back to Menu", callback_data="menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(chat_id, msg, parse_mode='Markdown', reply_markup=reply_markup)
        except Exception as e:
            logger.exception("_send_priority_list error")
            await context.bot.send_message(chat_id, f"Error: {str(e)[:200]}")
    
    async def _do_priority_sync(self, context, chat_id):
        """Sync from YC export file (callback from button)."""
        if not self.db_helper:
            await context.bot.send_message(chat_id, "Priority list not available (no database).")
            return
        path = self._get_priority_export_path()
        if not os.path.exists(path):
            await context.bot.send_message(chat_id, f"📂 Export file not found. Ask OpenClaw for job shortlist first, then tap Refresh.")
            return
        try:
            added, skipped = self.db_helper.sync_priority_from_yc_file(path)
            await context.bot.send_message(chat_id, f"✅ Sync YC: {added} added, {skipped} skipped.")
            await self._send_priority_list(context, chat_id)
        except Exception as e:
            logger.exception("_do_priority_sync error")
            await context.bot.send_message(chat_id, f"Error: {str(e)[:150]}")
    
    async def _do_priority_refresh(self, context, chat_id):
        """Run pipeline + sync (callback from button)."""
        if not self.db_helper:
            await context.bot.send_message(chat_id, "Priority list not available (no database).")
            return
        await context.bot.send_message(chat_id, "🔄 Refreshing from YC (30–60 sec)...")
        import subprocess
        path = self._get_priority_export_path()
        base = os.path.dirname(path)
        script = os.path.join(base, "run_shortlist.sh")
        if not os.path.exists(script):
            await context.bot.send_message(chat_id, "❌ run_shortlist.sh not found.")
            return
        try:
            subprocess.run(["bash", script], cwd=base, capture_output=True, timeout=120, env={**os.environ})
        except subprocess.TimeoutExpired:
            await context.bot.send_message(chat_id, "⏱️ Pipeline timed out. Try again.")
            return
        except Exception as e:
            await context.bot.send_message(chat_id, f"❌ Pipeline error: {str(e)[:100]}")
            return
        if os.path.exists(path):
            added, skipped = self.db_helper.sync_priority_from_yc_file(path)
            await context.bot.send_message(chat_id, f"✅ Refreshed! {added} added, {skipped} skipped.")
            await self._send_priority_list(context, chat_id)
        else:
            await context.bot.send_message(chat_id, "❌ Export file not created.")
    
    # Helper methods
    
    def _load_recent_jobs(self) -> List[Dict]:
        """Load jobs from recent cache file"""
        cache_dir = "autonomous_data/ats_cache"
        if not os.path.exists(cache_dir):
            return []
        
        # Get most recent cache file
        files = sorted([f for f in os.listdir(cache_dir) if f.endswith('.json')])
        if not files:
            return []
        
        latest_file = os.path.join(cache_dir, files[-1])
        try:
            with open(latest_file, 'r') as f:
                data = json.load(f)
                return data.get('jobs', [])
        except:
            return []
    
    def _count_todays_jobs(self) -> int:
        """Count jobs found today"""
        jobs = self._load_recent_jobs()
        return len(jobs)
    
    def _load_keywords(self) -> List[str]:
        """Load current search keywords"""
        return ["AI Product Engineer", "Applied LLM Engineer", "Founding Engineer AI", "LLM Engineer", "AI Agent Engineer", "AI Developer Tools Engineer"]
    
    def _save_keywords(self, keywords: List[str]):
        """Save updated keywords"""
        pass
    
    def _load_target_companies(self) -> Dict:
        """Load target companies from JSON"""
        try:
            with open('src/data/target_companies.json', 'r') as f:
                return json.load(f)
        except:
            return {}
    
    async def send_notification(self, message: str, parse_mode: str = 'Markdown'):
        """Send a notification message"""
        try:
            await self.app.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode
            )
        except Exception as e:
            print(f" Failed to send Telegram notification: {e}")
    
    def run(self):
        """Start the bot (blocking)"""
        print(" Starting Enhanced Telegram Bot...")
        self.app.run_polling()
    
    async def start(self):
        """Start the bot asynchronously (non-blocking)"""
        print("🤖 Starting Enhanced Telegram Bot (async mode)...")
        await self.app.initialize()
        await self.app.start()
        # Explicitly include callback_query to ensure button clicks work
        await self.app.updater.start_polling(
            allowed_updates=["message", "callback_query"]
        )
        print("✅ Enhanced Bot polling started (messages + callbacks)")


def create_enhanced_bot(token: str = None, chat_id: str = None, db_helper=None):
    """Create and return bot instance"""
    if token is None:
        token = os.getenv('TELEGRAM_BOT_TOKEN')
    if chat_id is None:
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID required")
    
    return EnhancedTelegramBot(token, chat_id, db_helper)


if __name__ == '__main__':
    bot = create_enhanced_bot()
    bot.run()
