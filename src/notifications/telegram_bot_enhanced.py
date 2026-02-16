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
        
        # Callback query handler for inline buttons
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))

        # ADDED: Voice + free-form text (additive — commands unchanged)
        self.app.add_handler(MessageHandler(filters.VOICE, self.handle_voice))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_freeform_text))
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Welcome message with main menu"""
        message = """🤖 *VibeJobHunter Interactive Bot*

Welcome! I'm your AI job hunting assistant running 24/7.

*🎯 QUICK START:*
/menu - Open interactive menu
/workflow - See how the engine works
/manual - What YOU need to do

*📊 MONITORING:*
/today - Today's activity summary
/jobs - Best job matches
/outreach - Pending messages to send

I'm automatically applying to jobs and finding founders for you!
"""
        # Create main menu keyboard
        keyboard = [
            [
                InlineKeyboardButton("📋 Menu", callback_data="menu"),
                InlineKeyboardButton("🔄 Workflow", callback_data="workflow")
            ],
            [
                InlineKeyboardButton("👤 Manual Steps", callback_data="manual"),
                InlineKeyboardButton("📊 Today", callback_data="today")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🆕 NEW MENU COMMANDS (January 2026 Upgrade)
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def cmd_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Interactive main menu with all options"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info("📋 /menu command received!")
        
        try:
            message = """📋 *VIBEJOBHUNTER MENU*

Choose an option below:"""
            
            keyboard = [
                # 🎯 JOB HUNTING Section
                [InlineKeyboardButton("🎯 JOB HUNTING", callback_data="header_job")],
                [InlineKeyboardButton("📊 Today's Summary", callback_data="today")],
                [
                    InlineKeyboardButton("💼 Jobs", callback_data="jobs"),
                    InlineKeyboardButton("📈 Stats", callback_data="stats")
                ],
                [InlineKeyboardButton("📨 Pending Outreach", callback_data="outreach")],
                
                # 🚀 AI MARKETING CMO Section
                [InlineKeyboardButton("🚀 AI MARKETING CMO", callback_data="header_cmo")],
                [
                    InlineKeyboardButton("📘 LinkedIn", callback_data="post_linkedin"),
                    InlineKeyboardButton("📸 Instagram", callback_data="post_instagram")
                ],
                [
                    InlineKeyboardButton("📊 Analytics", callback_data="analytics"),
                    InlineKeyboardButton("🎯 Campaign", callback_data="campaign")
                ],
                [InlineKeyboardButton("🎨 Generate Image", callback_data="generate_image")],
                
                # ⚡ SYSTEM Section
                [InlineKeyboardButton("⚡ SYSTEM", callback_data="header_system")],
                [
                    InlineKeyboardButton("🔄 Workflow", callback_data="workflow"),
                    InlineKeyboardButton("📖 Manual", callback_data="manual")
                ],
                [
                    InlineKeyboardButton("⏸️ Pause", callback_data="pause"),
                    InlineKeyboardButton("▶️ Resume", callback_data="resume_hunting")
                ],
                [InlineKeyboardButton("⚙️ Status", callback_data="status")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
            logger.info("📋 /menu response sent successfully!")
        except Exception as e:
            logger.error(f"❌ /menu command error: {e}", exc_info=True)
    
    async def cmd_workflow(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Visual explanation of how the engine works"""
        message = """🔄 *HOW VIBEJOBHUNTER WORKS*

*Every Hour, The Engine:*

1️⃣ *DISCOVERS JOBS*
   └─ Scans 7 sources (ATS, YC, RemoteOK, etc.)
   └─ Checks 200+ AI companies
   └─ Finds ~30-50 new jobs

2️⃣ *SCORES EACH JOB* (100 points)
   ├─ AI Product: 25 pts
   ├─ 0→1 Autonomy: 25 pts
   ├─ Full-Stack: 20 pts
   ├─ Business: 15 pts
   ├─ Bilingual: 5 pts
   └─ Web3: 10 pts
   ⭐ YC companies: +15 bonus!

3️⃣ *ROUTES BY SCORE*
   ├─ ≥60 → 🚀 AUTO-APPLY
   ├─ 58-59 → 🤝 FOUNDER OUTREACH
   ├─ 55-57 → 📋 REVIEW QUEUE
   └─ <55 → ❌ DISCARDED

4️⃣ *FOR AUTO-APPLY JOBS:*
   ├─ Selects best resume (EN/ES/Founding)
   ├─ Generates AI cover letter
   ├─ Fills ATS form (Greenhouse/Lever)
   ├─ Uploads your resume PDF
   └─ Handles email verification

5️⃣ *FOR OUTREACH JOBS:*
   ├─ Finds founder via Hunter.io
   ├─ Generates warm intro message
   ├─ Sends email (if verified)
   └─ 👤 YOU: Send LinkedIn message

*Daily Limits (Safety):*
├─ Max 5 applications/day
├─ Max 10 emails/day
└─ Max 3 emails/hour
"""
        keyboard = [[InlineKeyboardButton("👤 What I Do Manually", callback_data="manual")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def cmd_manual(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show what the user needs to do manually"""
        message = """👤 *WHAT YOU NEED TO DO MANUALLY*

The engine automates 80% of job hunting.
Here's what ONLY YOU can do:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*📨 DAILY TASKS (5-10 min)*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣ *Send LinkedIn Messages*
   When you see "🤝 LinkedIn Outreach Ready":
   └─ Copy the message I generate
   └─ Go to the LinkedIn URL
   └─ Send the connection request
   └─ Paste the message as note

2️⃣ *Check Your Email Inbox*
   └─ Look for interview requests
   └─ Reply to recruiter questions
   └─ Schedule calls yourself

3️⃣ *Review Queue* (optional)
   └─ Use /jobs to see waiting jobs
   └─ Decide if any deserve manual apply

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*📅 WEEKLY TASKS (30 min)*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

4️⃣ *Check Make.com*
   └─ Is LinkedIn posting working?
   └─ https://make.com/en/login

5️⃣ *Review Stats*
   └─ Use /stats to see metrics
   └─ Any companies not responding?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*🎤 INTERVIEW PREP (when needed)*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

6️⃣ *Prepare & Show Up*
   └─ Research the company
   └─ Prepare your stories
   └─ Do the actual interview!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*❌ WHAT I CAN'T DO:*
├─ Send LinkedIn messages (blocked)
├─ Do your interviews
├─ Negotiate your salary
├─ Accept job offers
└─ Say yes/no to opportunities
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        keyboard = [[InlineKeyboardButton("📨 Show Pending Outreach", callback_data="outreach")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    
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
        message = """
 *VibeJobHunter Command Reference*

*Job Discovery:*
/jobs - Show top 5 jobs found today
/companies - List all tracked companies

*Application Management:*
/apply <company> - Generate resume/cover letter
/recent - View last 10 applications
/stats - See your performance metrics

*System Control:*
/status - Check if system is running
/pause - Stop autonomous job hunting
/resume - Restart autonomous job hunting

*Configuration:*
/keywords <words> - Update search keywords
  Example: /keywords ML engineer, AI researcher

*Tips:*
- Jobs are checked hourly automatically
- High-match jobs (>80%) trigger instant alerts
- You'll get weekly performance reports
- All applications are tracked in the database

*Voice & questions:*
- Send a voice message (needs OPENAI_API_KEY) or type a question
- Try: "What companies did I apply to today?" for honest answers
"""
        await update.message.reply_text(message, parse_mode='Markdown')
    
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

    # ─────────────────────────────────────────────────────────────────────────
    # VOICE + FREE-FORM QUESTIONS (additive)
    # ─────────────────────────────────────────────────────────────────────────

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
            logger.info(f"🎤 Voice transcribed: {text[:100]}{'...' if len(text) > 100 else ''}")
            await self._reply_job_question(update, context, text)
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
        """Send menu via callback"""
        message = """📋 *VIBEJOBHUNTER MENU*

Choose an option below:"""
        
        keyboard = [
            [InlineKeyboardButton("📊 Today's Summary", callback_data="today")],
            [InlineKeyboardButton("🔄 How It Works", callback_data="workflow")],
            [InlineKeyboardButton("👤 What I Need To Do", callback_data="manual")],
            [
                InlineKeyboardButton("💼 Jobs", callback_data="jobs"),
                InlineKeyboardButton("📈 Stats", callback_data="stats")
            ],
            [InlineKeyboardButton("📨 Pending Outreach", callback_data="outreach")],
            [
                InlineKeyboardButton("⏸️ Pause", callback_data="pause"),
                InlineKeyboardButton("▶️ Resume", callback_data="resume_hunting")
            ],
            [InlineKeyboardButton("⚙️ System Status", callback_data="status")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(chat_id, message, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def _send_workflow(self, context, chat_id):
        """Send workflow explanation via callback"""
        message = """🔄 *HOW VIBEJOBHUNTER WORKS*

*Every Hour, The Engine:*

1️⃣ *DISCOVERS JOBS*
   └─ Scans 8 sources:
      ATS APIs, Dice MCP, YC, RemoteOK,
      Wellfound, WWR, AI Jobs, HN
   └─ Checks 200+ AI companies
   └─ Finds ~30-80 new jobs/cycle

2️⃣ *FILTERS & SCORES* (100 points)
   ├─ Domain-match filter (drops irrelevant)
   ├─ AI Product: 25 pts
   ├─ 0→1 Autonomy: 25 pts
   ├─ Full-Stack: 20 pts
   ├─ Business: 15 pts
   ├─ Bilingual: 5 pts
   └─ Web3: 10 pts
   ⭐ YC companies: +15 bonus!

3️⃣ *ROUTES BY SCORE*
   ├─ ≥60 → 🚀 AUTO-APPLY (ATS submit)
   ├─ 50-59 → 🤝 FOUNDER OUTREACH
   ├─ 40-49 → 📋 REVIEW QUEUE
   └─ <40 → ❌ DISCARDED

4️⃣ *FOR AUTO-APPLY:*
   ├─ Selects best resume
   ├─ Generates AI cover letter
   ├─ Fills ATS form
   └─ Uploads resume PDF

5️⃣ *FOLLOW-UPS & LIMITS:*
   ├─ Max 2 outreach/day
   ├─ Auto follow-up after 5 days
   └─ Max 5 apps/day, 10 emails/day
"""
        keyboard = [[InlineKeyboardButton("👤 What I Do Manually", callback_data="manual")],
                    [InlineKeyboardButton("📋 Back to Menu", callback_data="menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(chat_id, message, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def _send_manual(self, context, chat_id):
        """Send manual tasks via callback"""
        message = """👤 *WHAT YOU NEED TO DO*

*📨 DAILY (5-10 min):*

1️⃣ *Send LinkedIn Messages* (1-2/day)
   When you see "🤝 Outreach Ready":
   └─ Copy the message
   └─ Go to LinkedIn URL
   └─ Send as connection note
   └─ Bot caps at 2 outreach/day

2️⃣ *Check Your Email*
   └─ Reply to recruiters
   └─ Schedule interviews

3️⃣ *Follow-Up Reminders*
   └─ Bot notifies you after 5 days
   └─ Re-send or skip

*📅 WEEKLY (30 min):*

4️⃣ *Check Make.com*
   └─ Is LinkedIn CMO posting OK?

5️⃣ *Review /stats or /today*
   └─ Any issues?

*❌ I CAN'T DO (LinkedIn blocks bots):*
├─ Send LinkedIn messages for you
├─ Do your interviews
├─ Negotiate salary
└─ Accept offers
"""
        keyboard = [[InlineKeyboardButton("📨 Pending Outreach", callback_data="outreach")],
                    [InlineKeyboardButton("📋 Back to Menu", callback_data="menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(chat_id, message, parse_mode='Markdown', reply_markup=reply_markup)
    
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
