"""
🧠 AI-POWERED RESPONSE DETECTION & AUTO-TRIAGE

This is the GENIUS feature that closes the loop:
- Monitors inbox for responses to applications
- Uses Claude AI to classify: POSITIVE, REJECTION, QUESTION, SPAM
- Sends INSTANT Telegram alerts for hot leads
- Tracks outcomes for success prediction model
- Can auto-draft responses to questions

Author: VibeJobHunter + AI Co-Founders
Date: December 2025
Version: 1.0_GENIUS_RESPONSE_DETECTION
"""

import os
import re
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from enum import Enum
from dataclasses import dataclass
import imaplib
import email
from email.header import decode_header

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

RESPONSE_DETECTOR_VERSION = "1.0_GENIUS_RESPONSE_DETECTION"

class ResponseType(Enum):
    """Classification of email responses"""
    POSITIVE = "positive"          # Interview request, interest expressed
    REJECTION = "rejection"        # "We've decided to move forward with others"
    QUESTION = "question"          # "Can you tell me more about..."
    ACKNOWLEDGMENT = "ack"         # "We received your application"
    SPAM = "spam"                  # Unrelated, marketing, etc.
    UNKNOWN = "unknown"            # Needs manual review


@dataclass
class DetectedResponse:
    """A detected response from inbox"""
    email_id: str
    from_email: str
    from_name: str
    subject: str
    body_preview: str
    received_at: datetime
    response_type: ResponseType
    confidence: float
    company_name: Optional[str]
    suggested_action: str
    ai_analysis: str
    original_application_id: Optional[int] = None


# Keywords that indicate different response types (pre-filter before Claude)
POSITIVE_KEYWORDS = [
    "schedule", "interview", "call", "chat", "meeting", "availability",
    "interested", "move forward", "next steps", "like to speak",
    "when are you free", "calendar", "slot", "time to talk",
    "excited to", "love to connect", "great fit", "impressive"
]

REJECTION_KEYWORDS = [
    "unfortunately", "not moving forward", "other candidates",
    "not a fit", "position has been filled", "decided not to",
    "won't be moving forward", "not proceeding", "regret to inform",
    "not selected", "pursuing other", "competitive pool"
]

ACKNOWLEDGMENT_KEYWORDS = [
    "received your application", "thank you for applying",
    "application has been received", "we'll review", "review your application",
    "received your resume", "under review", "reviewing applications"
]

# Companies to watch for (from ATS scraper)
WATCHED_COMPANIES = [
    "anthropic", "openai", "deepmind", "xai", "meta", "google",
    "databricks", "scale", "perplexity", "runway", "cursor",
    "vercel", "figma", "stripe", "ramp", "brex", "modal",
    "anyscale", "together", "fireworks", "cohere", "jasper",
    "grammarly", "notion", "linear", "retool", "supabase"
]


class ResponseDetector:
    """
    AI-powered response detection and triage.
    
    Monitors inbox for responses to job applications and classifies them
    using Claude AI for intelligent triage.
    """
    
    def __init__(self):
        """Initialize response detector"""
        self.email_address = os.getenv("ZOHO_EMAIL", "aipa@aideazz.xyz")
        self.email_password = os.getenv("ZOHO_APP_PASSWORD")
        self.imap_connection = None
        self.anthropic_client = None
        
        # Track processed emails to avoid duplicates
        self.processed_email_ids = set()
        
        # Load Anthropic for AI classification
        try:
            from anthropic import Anthropic
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                self.anthropic_client = Anthropic(api_key=api_key)
                logger.info(f"✅ Response Detector initialized (v{RESPONSE_DETECTOR_VERSION})")
                logger.info(f"🔖 [FINGERPRINT: 2025-12-22_GENIUS_RESPONSE_DETECTION_DEPLOYED]")
            else:
                logger.warning("⚠️ No Anthropic API key - using keyword-only classification")
        except ImportError:
            logger.warning("⚠️ Anthropic not installed - using keyword-only classification")
        
        logger.info(f"📧 Monitoring: {self.email_address}")
        logger.info(f"👀 Watching for responses from {len(WATCHED_COMPANIES)} target companies")
    
    def connect(self) -> bool:
        """Connect to Zoho Mail via IMAP"""
        if not self.email_password:
            logger.error("❌ Cannot connect: No Zoho credentials")
            return False
        
        try:
            self.imap_connection = imaplib.IMAP4_SSL("imappro.zoho.com", 993)
            self.imap_connection.login(self.email_address, self.email_password)
            logger.info("✅ Connected to Zoho Mail for response detection")
            return True
        except Exception as e:
            logger.error(f"❌ IMAP connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close IMAP connection"""
        if self.imap_connection:
            try:
                self.imap_connection.logout()
            except:
                pass
            self.imap_connection = None
    
    def _extract_company_name(self, from_email: str, from_name: str, subject: str) -> Optional[str]:
        """Extract company name from email metadata"""
        # Check email domain
        domain_match = re.search(r"@([a-zA-Z0-9-]+)\.", from_email.lower())
        if domain_match:
            domain = domain_match.group(1)
            for company in WATCHED_COMPANIES:
                if company in domain:
                    return company.capitalize()
        
        # Check from name
        from_lower = from_name.lower()
        for company in WATCHED_COMPANIES:
            if company in from_lower:
                return company.capitalize()
        
        # Check subject
        subject_lower = subject.lower()
        for company in WATCHED_COMPANIES:
            if company in subject_lower:
                return company.capitalize()
        
        # Return domain as company name if nothing matches
        if domain_match:
            return domain_match.group(1).capitalize()
        
        return None
    
    def _keyword_classify(self, subject: str, body: str) -> Tuple[ResponseType, float]:
        """Quick classification using keywords (before Claude)"""
        text = f"{subject} {body}".lower()
        
        # Check for positive signals
        positive_count = sum(1 for kw in POSITIVE_KEYWORDS if kw in text)
        if positive_count >= 2:
            return ResponseType.POSITIVE, 0.7
        
        # Check for rejection signals
        rejection_count = sum(1 for kw in REJECTION_KEYWORDS if kw in text)
        if rejection_count >= 1:
            return ResponseType.REJECTION, 0.8
        
        # Check for acknowledgment
        ack_count = sum(1 for kw in ACKNOWLEDGMENT_KEYWORDS if kw in text)
        if ack_count >= 1:
            return ResponseType.ACKNOWLEDGMENT, 0.9
        
        # Check if it's from Greenhouse (verification email, not response)
        if "security code" in text or "verification" in text:
            return ResponseType.SPAM, 0.95  # Not a response, it's verification
        
        return ResponseType.UNKNOWN, 0.3
    
    async def _ai_classify(self, from_name: str, subject: str, body: str) -> Tuple[ResponseType, float, str, str]:
        """
        Use Claude AI for intelligent classification.
        
        Returns: (response_type, confidence, analysis, suggested_action)
        """
        if not self.anthropic_client:
            rtype, conf = self._keyword_classify(subject, body)
            return rtype, conf, "Keyword-based classification (no AI)", "Review manually"
        
        try:
            prompt = f"""You are analyzing an email response to a job application. Classify it and provide actionable advice.

FROM: {from_name}
SUBJECT: {subject}
BODY (first 1500 chars):
{body[:1500]}

Classify this email into ONE of these categories:
1. POSITIVE - Interview request, call scheduling, interest expressed, next steps
2. REJECTION - Not moving forward, position filled, pursuing other candidates
3. QUESTION - Asking for more info, clarification, portfolio review
4. ACKNOWLEDGMENT - Just confirming receipt, application under review
5. SPAM - Unrelated, marketing, newsletters, verification codes
6. UNKNOWN - Can't determine

Respond in this exact JSON format:
{{
    "classification": "POSITIVE|REJECTION|QUESTION|ACKNOWLEDGMENT|SPAM|UNKNOWN",
    "confidence": 0.0-1.0,
    "analysis": "Brief explanation of why this classification",
    "suggested_action": "What the applicant should do next",
    "urgency": "HIGH|MEDIUM|LOW|NONE"
}}

Be accurate. POSITIVE means they want to talk. ACKNOWLEDGMENT is just receipt confirmation."""

            response = self.anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result_text = response.content[0].text
            
            # Parse JSON from response
            json_match = re.search(r'\{[^{}]*\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                classification = result.get("classification", "UNKNOWN").upper()
                confidence = float(result.get("confidence", 0.5))
                analysis = result.get("analysis", "")
                action = result.get("suggested_action", "Review manually")
                
                type_map = {
                    "POSITIVE": ResponseType.POSITIVE,
                    "REJECTION": ResponseType.REJECTION,
                    "QUESTION": ResponseType.QUESTION,
                    "ACKNOWLEDGMENT": ResponseType.ACKNOWLEDGMENT,
                    "SPAM": ResponseType.SPAM,
                    "UNKNOWN": ResponseType.UNKNOWN
                }
                
                return type_map.get(classification, ResponseType.UNKNOWN), confidence, analysis, action
            
        except Exception as e:
            logger.error(f"❌ AI classification failed: {e}")
        
        # Fallback to keyword classification
        rtype, conf = self._keyword_classify(subject, body)
        return rtype, conf, "Fallback to keyword classification", "Review manually"
    
    def _parse_email(self, msg) -> Tuple[str, str, str, datetime]:
        """Extract email components"""
        # Get subject
        subject = ""
        raw_subject = msg.get("Subject", "")
        if raw_subject:
            decoded = decode_header(raw_subject)
            subject = decoded[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode('utf-8', errors='ignore')
        
        # Get from
        from_raw = msg.get("From", "")
        from_name = from_raw
        from_email = ""
        email_match = re.search(r'<([^>]+)>', from_raw)
        if email_match:
            from_email = email_match.group(1)
            from_name = from_raw.split('<')[0].strip().strip('"')
        else:
            from_email = from_raw
        
        # Get body
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = payload.decode('utf-8', errors='ignore')
                        break
                elif content_type == "text/html" and not body:
                    payload = part.get_payload(decode=True)
                    if payload:
                        html = payload.decode('utf-8', errors='ignore')
                        body = re.sub(r'<[^>]+>', ' ', html)  # Strip HTML
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode('utf-8', errors='ignore')
        
        # Get date
        date_str = msg.get("Date", "")
        try:
            received_at = email.utils.parsedate_to_datetime(date_str)
        except:
            received_at = datetime.now()
        
        return from_name, from_email, subject, body, received_at
    
    async def scan_for_responses(self, hours_back: int = 24) -> List[DetectedResponse]:
        """
        Scan inbox for responses to job applications.
        
        Args:
            hours_back: How many hours back to scan
            
        Returns:
            List of detected responses
        """
        logger.info(f"🔍 Scanning inbox for responses (last {hours_back} hours)...")
        
        if not self.imap_connection:
            if not self.connect():
                return []
        
        responses = []
        
        try:
            # Check INBOX
            self.imap_connection.select("INBOX")
            
            # Search for recent emails
            since_date = (datetime.now() - timedelta(hours=hours_back)).strftime("%d-%b-%Y")
            status, message_ids = self.imap_connection.search(None, f'(SINCE "{since_date}")')
            
            if status != "OK" or not message_ids[0]:
                logger.info("📭 No recent emails found")
                return []
            
            email_ids = message_ids[0].split()
            logger.info(f"📧 Found {len(email_ids)} recent emails to analyze")
            
            # Process each email (newest first)
            for email_id in reversed(email_ids[-50:]):  # Limit to 50 most recent
                # Skip if already processed
                if email_id in self.processed_email_ids:
                    continue
                
                try:
                    status, msg_data = self.imap_connection.fetch(email_id, "(RFC822)")
                    if status != "OK":
                        continue
                    
                    msg = email.message_from_bytes(msg_data[0][1])
                    from_name, from_email, subject, body, received_at = self._parse_email(msg)
                    
                    # Skip Greenhouse verification emails
                    if "security code" in subject.lower() or "greenhouse" in from_email.lower():
                        if "security code" in subject.lower():
                            self.processed_email_ids.add(email_id)
                            continue
                    
                    # Skip if too old
                    if received_at < datetime.now(received_at.tzinfo) - timedelta(hours=hours_back):
                        continue
                    
                    # Extract company name
                    company = self._extract_company_name(from_email, from_name, subject)
                    
                    # AI Classification
                    response_type, confidence, analysis, action = await self._ai_classify(
                        from_name, subject, body
                    )
                    
                    # Skip spam and low-confidence unknowns
                    if response_type == ResponseType.SPAM:
                        self.processed_email_ids.add(email_id)
                        continue
                    
                    # Create response object
                    detected = DetectedResponse(
                        email_id=email_id.decode() if isinstance(email_id, bytes) else str(email_id),
                        from_email=from_email,
                        from_name=from_name,
                        subject=subject,
                        body_preview=body[:500],
                        received_at=received_at,
                        response_type=response_type,
                        confidence=confidence,
                        company_name=company,
                        suggested_action=action,
                        ai_analysis=analysis
                    )
                    
                    responses.append(detected)
                    self.processed_email_ids.add(email_id)
                    
                    # Log significant responses
                    if response_type == ResponseType.POSITIVE:
                        logger.info(f"🔥 POSITIVE RESPONSE from {company or from_name}: {subject}")
                    elif response_type == ResponseType.QUESTION:
                        logger.info(f"❓ QUESTION from {company or from_name}: {subject}")
                    elif response_type == ResponseType.REJECTION:
                        logger.info(f"📭 Rejection from {company or from_name}")
                    
                except Exception as e:
                    logger.debug(f"Error processing email {email_id}: {e}")
                    continue
            
            # Summary
            positive_count = sum(1 for r in responses if r.response_type == ResponseType.POSITIVE)
            question_count = sum(1 for r in responses if r.response_type == ResponseType.QUESTION)
            rejection_count = sum(1 for r in responses if r.response_type == ResponseType.REJECTION)
            
            logger.info(f"📊 Response scan complete:")
            logger.info(f"   🔥 Positive (interviews): {positive_count}")
            logger.info(f"   ❓ Questions: {question_count}")
            logger.info(f"   📭 Rejections: {rejection_count}")
            
            return responses
            
        except Exception as e:
            logger.error(f"❌ Error scanning inbox: {e}")
            return []
    
    async def get_hot_leads(self, hours_back: int = 24) -> List[DetectedResponse]:
        """Get only positive responses and questions (hot leads)"""
        all_responses = await self.scan_for_responses(hours_back)
        return [r for r in all_responses if r.response_type in [ResponseType.POSITIVE, ResponseType.QUESTION]]
    
    def format_alert(self, response: DetectedResponse) -> str:
        """Format a response for Telegram alert"""
        emoji = {
            ResponseType.POSITIVE: "🔥🔥🔥",
            ResponseType.QUESTION: "❓",
            ResponseType.REJECTION: "📭",
            ResponseType.ACKNOWLEDGMENT: "✅",
            ResponseType.UNKNOWN: "❔"
        }.get(response.response_type, "📧")
        
        urgency = ""
        if response.response_type == ResponseType.POSITIVE:
            urgency = "\n⚡ URGENT: Respond within 24 hours!"
        
        return f"""{emoji} **{response.response_type.value.upper()}** from {response.company_name or 'Unknown'}

**From:** {response.from_name}
**Subject:** {response.subject}

**AI Analysis:** {response.ai_analysis}

**Suggested Action:** {response.suggested_action}{urgency}

**Preview:**
{response.body_preview[:300]}...
"""


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION WITH ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

async def check_for_responses_and_alert(telegram_notifier=None) -> List[DetectedResponse]:
    """
    Check for responses and send Telegram alerts for hot leads.
    
    Call this from orchestrator every hour or so.
    """
    detector = ResponseDetector()
    
    try:
        hot_leads = await detector.get_hot_leads(hours_back=24)
        
        if hot_leads and telegram_notifier:
            for lead in hot_leads:
                if lead.response_type == ResponseType.POSITIVE:
                    # HIGH PRIORITY - Interview request!
                    message = f"""🔥🔥🔥 **INTERVIEW REQUEST DETECTED!**

{detector.format_alert(lead)}

⚡ **DROP EVERYTHING AND RESPOND!**"""
                    await telegram_notifier.send_notification(message)
                    
                elif lead.response_type == ResponseType.QUESTION:
                    message = f"""❓ **Question from Recruiter**

{detector.format_alert(lead)}"""
                    await telegram_notifier.send_notification(message)
        
        return hot_leads
        
    finally:
        detector.disconnect()


# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE INTEGRATION (for success prediction)
# ═══════════════════════════════════════════════════════════════════════════════

def save_response_to_db(response: DetectedResponse, db_path: str = "autonomous_data/vibejobhunter.db"):
    """Save detected response to database for success prediction model"""
    import sqlite3
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create responses table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS detected_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id TEXT UNIQUE,
                from_email TEXT,
                from_name TEXT,
                subject TEXT,
                body_preview TEXT,
                received_at TIMESTAMP,
                response_type TEXT,
                confidence REAL,
                company_name TEXT,
                ai_analysis TEXT,
                suggested_action TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert response
        cursor.execute("""
            INSERT OR IGNORE INTO detected_responses 
            (email_id, from_email, from_name, subject, body_preview, received_at,
             response_type, confidence, company_name, ai_analysis, suggested_action)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            response.email_id,
            response.from_email,
            response.from_name,
            response.subject,
            response.body_preview,
            response.received_at.isoformat() if response.received_at else None,
            response.response_type.value,
            response.confidence,
            response.company_name,
            response.ai_analysis,
            response.suggested_action
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Saved response to database: {response.company_name} - {response.response_type.value}")
        
    except Exception as e:
        logger.error(f"❌ Failed to save response to DB: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

async def test_response_detector():
    """Test the response detector"""
    print("\n" + "=" * 60)
    print("🧠 TESTING AI RESPONSE DETECTOR")
    print("=" * 60 + "\n")
    
    detector = ResponseDetector()
    
    if not detector.email_password:
        print("❌ Cannot test: ZOHO_APP_PASSWORD not configured")
        return
    
    print("🔍 Scanning for responses...")
    responses = await detector.scan_for_responses(hours_back=48)
    
    print(f"\n📊 Found {len(responses)} responses:\n")
    
    for r in responses:
        print(f"{'🔥' if r.response_type == ResponseType.POSITIVE else '📧'} {r.response_type.value.upper()}")
        print(f"   From: {r.from_name} ({r.company_name or 'Unknown'})")
        print(f"   Subject: {r.subject}")
        print(f"   Confidence: {r.confidence:.0%}")
        print(f"   Action: {r.suggested_action}")
        print()
    
    detector.disconnect()
    print("✅ Test complete!")


if __name__ == "__main__":
    asyncio.run(test_response_detector())
