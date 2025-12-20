"""
AUTO-APPLICATOR v3: With Real ATS Submission
Generates tailored materials AND submits to ATS systems.

UPGRADED: December 2025
- Integrates with ats_submitter for real form submission
- Uses Playwright for Greenhouse/Lever/Ashby automation
- Dry-run mode by default (set ATS_DRY_RUN=false for live submission)
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import os
import json

from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

# Feature flag for ATS submission
ATS_SUBMISSION_ENABLED = os.getenv("ATS_SUBMISSION_ENABLED", "true").lower() == "true"

# === Application Decision Thresholds ===
AUTO_APPLY_SCORE = 65      # High-confidence auto-apply
REVIEW_SCORE = 55          # Queue for review / soft apply

# ELENA'S ACTUAL BACKGROUND (from resume)
ELENA_BACKGROUND = """
ABOUT ELENA REVICHEVA:

CORE IDENTITY:
- AI-First Engineer & Startup Founder
- Building Emotionally Intelligent AI at AIdeazz.xyz
- Located in Panama City, Panama (Remote/On-site/Full-time/Part-time)
- Bilingual: EN/ES (also Russian native, French elementary)

KEY ACHIEVEMENTS:
• 11 AI products in 10 months (March-December 2025) - solo-built full-stack
• Deployed AI Co-Founders: CTO AIPA (autonomous code reviewer) + CMO AIPA (LinkedIn automation)
• 99%+ cost reduction vs team-based development ($900K → <$15K)
• Users in 19 Spanish-speaking countries
• PayPal subscriptions LIVE, crypto payments testing

TECHNICAL EXPERTISE:
AI/ML: Claude · GPT · Groq (Llama 3.3) · Whisper · TTS · MCP · LangChain · ElizaOS
Languages: Python · TypeScript · JavaScript · Node.js · SQL
Frameworks: React · Flask · FastAPI · Express.js · Vite
Infrastructure: PostgreSQL · Oracle Autonomous DB · Supabase · Docker · Railway · Oracle Cloud
Frontend: Tailwind CSS · shadcn/ui · Framer Motion · i18next
APIs: WhatsApp · Telegram · PayPal · Twitter · GitHub API · Make.com · Buffer
Web3: Polygon · Thirdweb · MetaMask · IPFS · DAO Design

MAJOR PRODUCTS:
1. CTO AIPA - Autonomous code review across 8 GitHub repos (Oracle Cloud, $0/month)
2. CMO AIPA - AI Marketing Co-Founder with strategic content generation (Railway)
3. EspaLuz - WhatsApp/Telegram Spanish tutor with emotional memory (19 countries)
4. ALGOM Alpha - AI crypto mentor on Twitter with paper trading
5. Atuona NFT Gallery - Poetry NFTs on Polygon

PREVIOUS EXPERIENCE:
- Operational Co-Founder at OmniBazaar (DAO LLC structure, tokenomics)
- Deputy CEO & CLO at JSC "E-GOV OPERATOR" Russia (2011-2018) - Digital transformation
- Deputy CEO at Fundery LLC Russia (2017-2018) - ICO compliance

EDUCATION:
- Polkadot Blockchain Academy PBA-X Wave #3 (2025)
- How-To-DAO Cohort Graduate (2025)
- M.A. Social Psychology, Penza State University (2018)
- Blockchain Regulation, MGIMO (2017)

TARGET ROLES:
AI Product Manager | Full-Stack AI Engineer | Founding Engineer | LLM Engineer | 
AI Solutions Architect | AI Growth Engineer | Technical Lead

UNIQUE VALUE:
- Proven 0→1 AI-First Builder: 10x faster shipping with 99%+ cost reduction
- Full-Stack: End-to-end ownership from vision to deployment to growth
- Web3 native and bilingual - next-gen AI that evolves with humans
"""


class AutoApplicatorV2:
    """
    Auto-application system using Elena's REAL background
    """
    
    def __init__(self, profile, db_helper=None, email_service=None, telegram=None):
        self.profile = profile
        self.db_helper = db_helper
        self.email_service = email_service
        self.telegram = telegram
        
        # Initialize Claude
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            self.claude = AsyncAnthropic(api_key=api_key)
        else:
            logger.warning("⚠️ ANTHROPIC_API_KEY not set")
            self.claude = None
        
        # Create output directories
        self.output_dir = Path("autonomous_data/applications")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("✅ AutoApplicatorV2 initialized with Elena's real background")
    
    async def generate_cover_letter(self, job: Dict[str, Any]) -> Optional[str]:
        """
        Generate tailored cover letter using Elena's REAL background
        """
        if not self.claude:
            return None
        
        company = job.get('company', 'Unknown')
        title = job.get('title', 'Unknown')
        description = job.get('description', '')[:2000]  # First 2000 chars
        
        prompt = f"""You are helping Elena Revicheva apply for a job. Write a compelling, authentic cover letter.

{ELENA_BACKGROUND}

JOB DETAILS:
Company: {company}
Role: {title}
Description: {description}

INSTRUCTIONS:
1. **BE SPECIFIC**: Reference Elena's actual projects (CTO AIPA, CMO AIPA, EspaLuz, ALGOM)
2. **SHOW IMPACT**: Use real metrics (11 products in 10 months, 99% cost reduction, $0/month ops)
3. **MATCH THE ROLE**: 
   - AI Engineer → Focus on Claude/GPT integration, LangChain, MCP
   - Founding Engineer → Highlight 0→1 building, full-stack, rapid shipping
   - Product Role → Emphasize product launches, user traction (19 countries)
   - Technical Lead → Show architecture (Oracle Cloud, Railway, autonomous systems)
4. **BE AUTHENTIC**: Elena is a founder who BUILDS, not just talks. Show concrete examples.
5. **KEEP IT CONCISE**: 3 paragraphs max
6. **NO CLICHÉS**: Skip "I am writing to express interest" - start with impact

FORMAT:
- NO "Dear Hiring Manager" opening
- Start directly with a strong hook
- End with clear next step (not "I look forward to hearing from you")

TONE: Confident, founder-minded, technical but accessible

Write the cover letter now:"""

        try:
            response = await self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            cover_letter = response.content[0].text.strip()
            return cover_letter
            
        except Exception as e:
            logger.error(f"Failed to generate cover letter: {e}")
            return None
    
    async def process_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single job application with intelligent resume selection"""
        company = job.get('company', 'Unknown')
        title = job.get('title', 'Unknown')
        
        logger.info(f"🎯 Processing: {title} at {company}")
        
        result = {
            'company': company,
            'title': title,
            'url': job.get('url'),
            'match_score': job.get('match_score', 0),
            'materials_generated': False,
            'email_sent': False,
            'db_tracked': False,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # ──────────────────────────────────
            # SELECT OPTIMAL RESUME VARIANT
            # ──────────────────────────────────
            resume_type = "default"
            resume_pdf_path = None
            try:
                from ..templates.resume_selector import get_resume_selector
                selector = get_resume_selector()
                resume_content, resume_type = selector.get_resume_for_job(job)
                # Also get PDF path for ATS submission
                resume_pdf_path, _ = selector.get_pdf_path_for_job(job)
                result['resume_variant'] = resume_type
                result['resume_pdf_path'] = resume_pdf_path
                logger.info(f"  📄 Selected resume: {resume_type}")
            except Exception as e:
                logger.debug(f"Resume selector unavailable: {e}")
                resume_content = None
            
            # Generate cover letter
            logger.info(f"  📝 Generating materials...")
            cover_letter = await self.generate_cover_letter(job)
            
            if not cover_letter:
                logger.error(f"  ❌ Failed to generate materials")
                return result
            
            # Save application package
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            company_slug = company.replace(' ', '_').replace('/', '_').lower()
            filename = f"application_{company_slug}_{timestamp}.txt"
            filepath = self.output_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"═══════════════════════════════════════════════════════════════════════════════\n")
                f.write(f"APPLICATION PACKAGE - {company.upper()}\n")
                f.write(f"═══════════════════════════════════════════════════════════════════════════════\n\n")
                f.write(f"Company: {company}\n")
                f.write(f"Role: {title}\n")
                f.write(f"Applied: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Match Score: {job.get('match_score', 0)}/100\n")
                f.write(f"Resume Variant: {resume_type}\n")
                f.write(f"URL: {job.get('url', 'N/A')}\n")
                
                # Include founder info if available
                founder_info = job.get('founder_info')
                if founder_info:
                    f.write(f"\n--- FOUNDER INFO ---\n")
                    f.write(f"LinkedIn: {founder_info.get('linkedin_company', 'N/A')}\n")
                    f.write(f"Email patterns: {founder_info.get('email_patterns', [])[:3]}\n")
                
                f.write(f"\n{'═'*80}\n")
                f.write(f"COVER LETTER\n")
                f.write(f"{'═'*80}\n\n")
                f.write(cover_letter)
                
                # Include resume if available
                if resume_content:
                    f.write(f"\n\n{'═'*80}\n")
                    f.write(f"RESUME ({resume_type.upper()})\n")
                    f.write(f"{'═'*80}\n\n")
                    f.write(resume_content[:3000])  # First 3000 chars
            
            result['materials_generated'] = True
            result['cover_letter_path'] = str(filepath)
            logger.info(f"    ✅ Saved: {filename}")
            
            # ──────────────────────────────────
            # NEW: ATS Form Submission (if enabled)
            # ──────────────────────────────────
            if ATS_SUBMISSION_ENABLED and job.get('url'):
                try:
                    from .ats_submitter import ATSSubmitter
                    
                    async with ATSSubmitter() as submitter:
                        ats_type = submitter._detect_ats_type(job.get('url', ''), job.get('source', ''))
                        
                        if ats_type != 'unknown':
                            logger.info(f"    🚀 Submitting to {ats_type}...")
                            
                            # Use selected PDF resume or fallback to env var
                            ats_resume_path = resume_pdf_path or os.getenv('RESUME_PATH') or submitter.resume_path
                            
                            submission_result = await submitter.submit_application(
                                job=job,
                                cover_letter=cover_letter,
                                resume_path=ats_resume_path
                            )
                            
                            result['ats_submitted'] = submission_result.success
                            result['ats_type'] = ats_type
                            result['ats_dry_run'] = submission_result.dry_run
                            result['ats_confirmation'] = submission_result.confirmation_id
                            
                            if submission_result.success:
                                if submission_result.dry_run:
                                    logger.info(f"    🔒 DRY RUN: Would submit to {ats_type}")
                                else:
                                    logger.info(f"    ✅ ATS submitted: {submission_result.confirmation_id}")
                            else:
                                logger.warning(f"    ⚠️ ATS submission failed: {submission_result.error}")
                        else:
                            logger.debug(f"    ℹ️ Unknown ATS type - skipping form submission")
                            
                except ImportError:
                    logger.debug("    ℹ️ ATS submitter not available (playwright not installed)")
                except Exception as e:
                    logger.warning(f"    ⚠️ ATS submission error: {e}")
            
            # Send email (if configured)
            if self.email_service:
                logger.info(f"  📧 Sending application...")
                
                # Get founder info for personalized outreach
                founder_info = job.get('founder_info')
                match_score = job.get('match_score', 0)
                
                # Determine email target (prioritize founder for high-score jobs)
                hiring_email = None
                is_founder_outreach = False
                
                # HIGH-SCORE (75+): Try founder email first
                if match_score >= 75 and founder_info:
                    email_patterns = founder_info.get('email_patterns', [])
                    domain = founder_info.get('domain', '')
                    
                    # Get primary founder name if available
                    primary_founder = founder_info.get('primary_founder', {})
                    founder_name = primary_founder.get('name', '') if isinstance(primary_founder, dict) else ''
                    
                    if email_patterns and domain:
                        # Prioritize: founder@ > hello@ > hi@ > contact@
                        priority_prefixes = ['founder', 'hello', 'hi', 'contact', 'team']
                        for prefix in priority_prefixes:
                            for pattern in email_patterns:
                                if pattern.startswith(f"{prefix}@"):
                                    hiring_email = pattern
                                    is_founder_outreach = True
                                    break
                            if hiring_email:
                                break
                        
                        # Fallback to first pattern
                        if not hiring_email and email_patterns:
                            hiring_email = email_patterns[0]
                            is_founder_outreach = True
                
                # MEDIUM-SCORE (50-74): Use careers/jobs email
                if not hiring_email:
                    hiring_email = job.get('email')
                    if not hiring_email:
                        domain = company.lower().replace(' ', '').replace(',', '').replace('.', '')
                        hiring_email = f"careers@{domain}.com"
                
                try:
                    # Use founder outreach template for high-score matches
                    if is_founder_outreach:
                        logger.info(f"    👤 FOUNDER OUTREACH: {hiring_email}")
                        email_result = await self._send_founder_email(
                            to=hiring_email,
                            company=company,
                            role=title,
                            cover_letter=cover_letter,
                            founder_info=founder_info
                        )
                    else:
                        email_result = await self.email_service.send_application_email(
                            to=hiring_email,
                            company=company,
                            role=title,
                            cover_letter=cover_letter
                        )
                    
                    result['email_sent'] = email_result.get('success', False)
                    result['email_to'] = hiring_email
                    result['is_founder_outreach'] = is_founder_outreach
                    
                    if result['email_sent']:
                        logger.info(f"    ✅ Email sent to {hiring_email}" + (" (FOUNDER)" if is_founder_outreach else ""))
                    else:
                        logger.warning(f"    ⚠️ Email failed: {email_result.get('error')}")
                        
                except Exception as e:
                    logger.error(f"    ❌ Email error: {e}")
            
            # Track in database
            if self.db_helper:
                try:
                    # Create job_id and application_data separately (method signature requires both)
                    job_id = f"{company}_{title}".replace(' ', '_').replace('/', '_')[:100]
                    application_data = {
                        'id': f"app_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{company_slug}",
                        'applied_date': datetime.now(),
                        'source': job.get('source', 'ats_scraper'),
                        'resume_version': resume_type,
                        'cover_letter_hash': str(filepath),
                    }
                    self.db_helper.record_application(job_id, application_data)
                    result['db_tracked'] = True
                    logger.info(f"    ✅ Tracked in database")
                except Exception as e:
                    logger.error(f"    ⚠️ DB tracking failed: {e}")
            
            # Notify Telegram
            if self.telegram and result['materials_generated']:
                try:
                    await self.telegram.send_message(
                        f"✅ Applied: {company}\n"
                        f"📋 {title}\n"
                        f"📊 Score: {job.get('match_score', 0)}\n"
                        f"📧 {'Sent' if result['email_sent'] else 'Materials ready'}"
                    )
                except Exception as e:
                    logger.error(f"    ⚠️ Telegram notify failed: {e}")
            
            logger.info(f"  ✅ Complete: {company}")
            return result
            
        except Exception as e:
            logger.error(f"  ❌ Error processing {company}: {e}")
            result['error'] = str(e)
            return result
    
    async def _send_founder_email(
        self,
        to: str,
        company: str,
        role: str,
        cover_letter: str,
        founder_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send personalized founder outreach email
        
        This uses a more direct, founder-to-founder tone vs generic application
        """
        if not self.email_service:
            return {'success': False, 'error': 'Email service not configured'}
        
        # Extract founder name if available
        primary_founder = founder_info.get('primary_founder', {})
        founder_name = primary_founder.get('name', '') if isinstance(primary_founder, dict) else ''
        
        # Generate personalized subject line
        if founder_name:
            subject = f"Fellow founder → {role} at {company}"
        else:
            subject = f"AI Builder → {role} at {company}"
        
        # Create founder-focused email body
        # Less formal, more direct - founder to founder
        email_body = f"""Hi{' ' + founder_name.split()[0] if founder_name else ''},

I'm Elena — an AI-first founder who's shipped 11 products solo in 10 months. I saw the {role} opening and wanted to reach out directly.

Quick highlights:
• Built 2 autonomous AI Co-Founders (CTO + CMO) that run my company while I sleep
• 99%+ cost reduction vs team-based dev ($900K → <$15K)
• Full-stack: Python/TS/React → Claude/GPT/LangChain → PostgreSQL/Docker/Railway
• Users across 19 countries, PayPal subscriptions live

{cover_letter}

I'd love 15 minutes to chat about how my scrappy shipping speed could help {company}.

Elena Revicheva
🔗 linkedin.com/in/elenarevicheva
🌐 aideazz.xyz
📧 aipa@aideazz.xyz
"""
        
        try:
            result = await self.email_service.send_email(
                to=to,
                subject=subject,
                body=email_body,
                is_html=False
            )
            return result
        except Exception as e:
            # Fallback to standard application email
            logger.warning(f"Founder email failed, using standard: {e}")
            return await self.email_service.send_application_email(
                to=to,
                company=company,
                role=role,
                cover_letter=cover_letter
            )
    
    async def batch_process_jobs(
        self, 
        jobs: List[Dict[str, Any]], 
        max_applications: int = 3
    ) -> Dict[str, Any]:
        """Process multiple jobs in batch with intelligent threshold-based decisions"""
        logger.info(f"🚀 Processing {len(jobs)} jobs (max {max_applications})")
        
        results = []
        auto_applied = 0
        queued_for_review = 0
        skipped = 0
        
        for i, job in enumerate(jobs[:max_applications], 1):
            score = job.get('match_score', 0)
            
            # ═══════════════════════════════════════════════
            # THRESHOLD-BASED DECISION LOGIC
            # ═══════════════════════════════════════════════
            
            if score >= AUTO_APPLY_SCORE:
                # HIGH CONFIDENCE: Auto-apply immediately
                logger.info(f"\n📍 Job {i}/{min(len(jobs), max_applications)} - 🚀 AUTO-APPLY (score: {score})")
                result = await self.process_job(job)
                result['decision'] = 'auto_apply'
                results.append(result)
                auto_applied += 1
                
            elif score >= REVIEW_SCORE:
                # MEDIUM CONFIDENCE: Queue for human review
                logger.info(f"\n📍 Job {i}/{min(len(jobs), max_applications)} - 📋 REVIEW QUEUE (score: {score})")
                
                # Generate materials but don't send yet
                result = await self.process_job(job)
                result['decision'] = 'review'
                result['needs_human_review'] = True
                results.append(result)
                queued_for_review += 1
                
            else:
                # LOW CONFIDENCE: Skip
                logger.info(f"\n📍 Job {i}/{min(len(jobs), max_applications)} - ⏭️  SKIP (score: {score} < {REVIEW_SCORE})")
                result = {
                    'company': job.get('company', 'Unknown'),
                    'title': job.get('title', 'Unknown'),
                    'match_score': score,
                    'decision': 'skip',
                    'reason': f'Score below review threshold ({REVIEW_SCORE})',
                    'timestamp': datetime.now().isoformat()
                }
                results.append(result)
                skipped += 1
                continue
            
            # Rate limiting (only for jobs we actually processed)
            if score >= REVIEW_SCORE and i < min(len(jobs), max_applications):
                await asyncio.sleep(5)
        
        # ═══════════════════════════════════════════════
        # SUMMARY
        # ═══════════════════════════════════════════════
        summary = {
            'total_jobs': len(jobs),
            'processed': len(results),
            'auto_applied': auto_applied,
            'queued_for_review': queued_for_review,
            'skipped': skipped,
            'materials_generated': sum(1 for r in results if r.get('materials_generated')),
            'emails_sent': sum(1 for r in results if r.get('email_sent')),
            'ats_submitted': sum(1 for r in results if r.get('ats_submitted')),
            'db_tracked': sum(1 for r in results if r.get('db_tracked')),
            'errors': sum(1 for r in results if 'error' in r),
            'thresholds': {
                'auto_apply': AUTO_APPLY_SCORE,
                'review': REVIEW_SCORE
            },
            'results': results,
            'timestamp': datetime.now().isoformat()
        }
        
        # Log summary
        logger.info(f"\n{'═'*60}")
        logger.info(f"📊 BATCH COMPLETE:")
        logger.info(f"  Jobs processed: {summary['processed']}/{summary['total_jobs']}")
        logger.info(f"  🚀 Auto-applied: {auto_applied} (score ≥ {AUTO_APPLY_SCORE})")
        logger.info(f"  📋 Review queue: {queued_for_review} (score {REVIEW_SCORE}-{AUTO_APPLY_SCORE-1})")
        logger.info(f"  ⏭️  Skipped: {skipped} (score < {REVIEW_SCORE})")
        logger.info(f"  📝 Materials: {summary['materials_generated']}")
        logger.info(f"  📧 Emails sent: {summary['emails_sent']}")
        logger.info(f"  🤖 ATS submitted: {summary['ats_submitted']}")
        logger.info(f"  💾 DB tracked: {summary['db_tracked']}")
        logger.info(f"{'═'*60}")
        
        # Save summary
        summary_file = self.output_dir / f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"📄 Summary saved: {summary_file.name}")
        
        return summary


# For backwards compatibility
AutoApplicator = AutoApplicatorV2


async def test_applicator():
    """Test with sample AI Engineer jobs at different score levels"""
    sample_jobs = [
        {
            'company': 'Anthropic',
            'title': 'AI Engineer',
            'description': '''We're looking for an AI Engineer to help build Claude. 
            You'll work on LLM integration, prompt engineering, and AI product development.
            Experience with Python, React, and AI APIs required.''',
            'url': 'https://anthropic.com/careers',
            'match_score': 95,  # Should AUTO-APPLY
            'source': 'greenhouse'
        },
        {
            'company': 'YC Startup',
            'title': 'Founding Engineer',
            'description': '''Early-stage startup building AI tools. Looking for a full-stack
            engineer who can ship fast and wear many hats.''',
            'url': 'https://example.com/job',
            'match_score': 60,  # Should go to REVIEW
            'source': 'yc_workatastartup'
        },
        {
            'company': 'BigCorp',
            'title': 'Junior Developer',
            'description': '''Entry-level position maintaining legacy Java systems.
            No AI experience required.''',
            'url': 'https://example.com/job2',
            'match_score': 35,  # Should SKIP
            'source': 'linkedin'
        }
    ]
    
    applicator = AutoApplicatorV2(profile=None)
    summary = await applicator.batch_process_jobs(sample_jobs, max_applications=3)
    
    print("\n" + "="*80)
    print("✅ TEST COMPLETE")
    print("="*80)
    print(f"\n📊 Results:")
    print(f"  Auto-applied: {summary['auto_applied']}")
    print(f"  Review queue: {summary['queued_for_review']}")
    print(f"  Skipped: {summary['skipped']}")
    print(f"\n💡 Thresholds used:")
    print(f"  AUTO_APPLY_SCORE: {AUTO_APPLY_SCORE}")
    print(f"  REVIEW_SCORE: {REVIEW_SCORE}")


if __name__ == '__main__':
    asyncio.run(test_applicator())