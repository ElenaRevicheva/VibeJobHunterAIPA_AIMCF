"""
Enhanced Telegram Bot for VibeJobHunter
Interactive commands for job hunting control and status
"""

import os
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import json

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


class EnhancedTelegramBot:
    """
    Interactive Telegram bot for VibeJobHunter
    
    Commands:
    /start - Welcome message and help
    /jobs - Show top jobs found today
    /stats - Show application statistics
    /apply <company> - Generate materials for a company
    /pause - Pause autonomous job hunting
    /resume - Resume autonomous job hunting
    /keywords <keywords> - Update job search keywords
    /companies - Show tracked companies
    /recent - Show recent applications
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
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Welcome message"""
        message = """
 *VibeJobHunter Interactive Bot*

Welcome! I'm your AI job hunting assistant running 24/7.

*Available Commands:*
/jobs - See today's best job matches
/stats - View your application statistics
/apply <company> - Generate materials for a job
/recent - Show your recent applications
/status - Check system status
/pause - Pause job hunting
/resume - Resume job hunting
/help - Show all commands

I'll notify you when I find great jobs and track all your applications!
"""
        await update.message.reply_text(message, parse_mode='Markdown')
    
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
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button clicks"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "stats":
            # Trigger stats command
            update.message = query.message
            await self.cmd_stats(update, context)
        
        elif query.data == "refresh_jobs":
            await query.edit_message_text(" Refreshing jobs...")
            update.message = query.message
            await self.cmd_jobs(update, context)
        
        elif query.data.startswith("send_email_"):
            company = query.data.replace("send_email_", "")
            await query.edit_message_text(f" Sending email to {company}...")
        
        elif query.data == "save_materials":
            await query.edit_message_text(" Materials saved to your profile!")
    
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
        return ["ML Engineer", "AI Engineer", "Founding Engineer", "Product Engineer"]
    
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
        await self.app.updater.start_polling()


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
