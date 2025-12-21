"""
🔐 GREENHOUSE EMAIL VERIFICATION HANDLER

Greenhouse uses email verification as anti-spam protection.
When submitting an application:
1. Fill form and submit
2. Greenhouse sends verification code to applicant email
3. Enter code into form and resubmit

This module:
- Reads verification emails from Zoho Mail via IMAP
- Extracts the security code
- Returns it for form submission

Author: VibeJobHunter
Date: December 2025
"""

import imaplib
import email
from email.header import decode_header
import re
import os
import logging
import asyncio
from typing import Optional, Tuple, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# Zoho IMAP settings
# Note: For Zoho Mail Pro/Business accounts, use imappro.zoho.com
# For free Zoho Mail accounts, use imap.zoho.com
ZOHO_IMAP_HOST = os.getenv("ZOHO_IMAP_HOST", "imappro.zoho.com")
ZOHO_IMAP_PORT = 993

# Greenhouse email patterns
GREENHOUSE_SENDER = "no-reply@us.greenhouse-mail.io"
GREENHOUSE_SUBJECT_PATTERN = r"Security code for your application"
GREENHOUSE_CODE_PATTERN = r"Copy and paste this code[^\n]*\n\s*([A-Za-z0-9]{8})"

# How long to wait for verification email
MAX_WAIT_SECONDS = 120  # 2 minutes
CHECK_INTERVAL_SECONDS = 5  # Check every 5 seconds


class GreenhouseEmailVerifier:
    """
    Handles Greenhouse email verification flow.
    
    Connects to Zoho Mail via IMAP to read verification codes.
    """
    
    def __init__(self):
        """Initialize with Zoho credentials from environment"""
        self.email_address = os.getenv("ZOHO_EMAIL", "aipa@aideazz.xyz")
        self.email_password = os.getenv("ZOHO_APP_PASSWORD")  # App-specific password
        
        # Alternative: Use regular password if app password not set
        if not self.email_password:
            self.email_password = os.getenv("ZOHO_PASSWORD")
        
        self.imap_connection = None
        
        if not self.email_password:
            logger.warning("⚠️ Zoho email credentials not configured")
            logger.info("   Set ZOHO_APP_PASSWORD or ZOHO_PASSWORD in environment")
        else:
            logger.info("✅ Greenhouse Email Verifier initialized")
    
    def connect(self) -> bool:
        """
        Connect to Zoho Mail via IMAP
        
        Returns:
            bool: True if connection successful
        """
        if not self.email_password:
            logger.error("❌ Cannot connect: No Zoho credentials")
            logger.error(f"   ZOHO_EMAIL set: {bool(os.getenv('ZOHO_EMAIL'))}")
            logger.error(f"   ZOHO_APP_PASSWORD set: {bool(os.getenv('ZOHO_APP_PASSWORD'))}")
            return False
        
        try:
            # Log connection attempt (without password)
            logger.info(f"🔌 Connecting to {ZOHO_IMAP_HOST}:{ZOHO_IMAP_PORT}")
            logger.info(f"   Email: {self.email_address}")
            logger.info(f"   Password length: {len(self.email_password)} chars")
            
            self.imap_connection = imaplib.IMAP4_SSL(ZOHO_IMAP_HOST, ZOHO_IMAP_PORT)
            self.imap_connection.login(self.email_address, self.email_password)
            logger.info(f"✅ Connected to Zoho Mail: {self.email_address}")
            return True
        except imaplib.IMAP4.error as e:
            logger.error(f"❌ IMAP login failed: {e}")
            logger.error(f"   Server: {ZOHO_IMAP_HOST}")
            logger.error(f"   Email used: {self.email_address}")
            logger.error(f"   Password length: {len(self.email_password)} chars")
            logger.info("   💡 Try using an App-specific password from Zoho settings")
            logger.info("   💡 Make sure IMAP is enabled in Zoho Mail settings")
            return False
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close IMAP connection"""
        if self.imap_connection:
            try:
                self.imap_connection.logout()
                logger.info("📪 Disconnected from Zoho Mail")
            except Exception:
                pass
            self.imap_connection = None
    
    def _extract_code_from_email(self, msg) -> Optional[str]:
        """
        Extract verification code from email message
        
        Args:
            msg: email.message.Message object
        
        Returns:
            str: 8-character verification code or None
        """
        try:
            # Get email body
            body = ""
            
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode('utf-8', errors='ignore')
                            break
                    elif content_type == "text/html":
                        payload = part.get_payload(decode=True)
                        if payload:
                            # Strip HTML tags for code extraction
                            html_body = payload.decode('utf-8', errors='ignore')
                            body = re.sub(r'<[^>]+>', '', html_body)
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode('utf-8', errors='ignore')
            
            # Extract code using pattern
            # Look for 8-character alphanumeric code
            patterns = [
                r"Copy and paste this code[^\n]*\n\s*([A-Za-z0-9]{8})",
                r"security code field[^\n]*\n\s*([A-Za-z0-9]{8})",
                r"\n([A-Za-z0-9]{8})\n",  # Standalone 8-char code on its own line
            ]
            
            for pattern in patterns:
                match = re.search(pattern, body, re.IGNORECASE)
                if match:
                    code = match.group(1)
                    logger.info(f"✅ Found verification code: {code}")
                    return code
            
            logger.warning("⚠️ Could not extract code from email body")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error extracting code: {e}")
            return None
    
    def get_latest_greenhouse_code(self, company: str = None, max_age_minutes: int = 10) -> Optional[str]:
        """
        Get the most recent Greenhouse verification code from inbox
        
        Args:
            company: Optional company name to filter (e.g., "xAI")
            max_age_minutes: Only consider emails newer than this
        
        Returns:
            str: Verification code or None
        """
        if not self.imap_connection:
            if not self.connect():
                return None
        
        try:
            # Select inbox
            self.imap_connection.select("INBOX")
            
            # Search for Greenhouse emails
            # Search criteria: FROM greenhouse AND recent
            search_criteria = f'(FROM "{GREENHOUSE_SENDER}")'
            
            status, message_ids = self.imap_connection.search(None, search_criteria)
            
            if status != "OK" or not message_ids[0]:
                logger.info("📭 No Greenhouse verification emails found")
                return None
            
            # Get list of email IDs
            email_ids = message_ids[0].split()
            
            # Check emails from newest to oldest
            for email_id in reversed(email_ids[-10:]):  # Check last 10 emails
                status, msg_data = self.imap_connection.fetch(email_id, "(RFC822)")
                
                if status != "OK":
                    continue
                
                msg = email.message_from_bytes(msg_data[0][1])
                
                # Check subject
                subject = decode_header(msg["Subject"])[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode('utf-8', errors='ignore')
                
                if "security code" not in subject.lower():
                    continue
                
                # Check if company matches (if specified)
                if company and company.lower() not in subject.lower():
                    continue
                
                # Check email date
                date_str = msg.get("Date", "")
                try:
                    # Parse email date (simplified - just check if recent)
                    email_date = email.utils.parsedate_to_datetime(date_str)
                    age = datetime.now(email_date.tzinfo) - email_date
                    
                    if age > timedelta(minutes=max_age_minutes):
                        logger.debug(f"📧 Email too old: {age}")
                        continue
                except Exception:
                    # If date parsing fails, try anyway
                    pass
                
                # Extract code
                code = self._extract_code_from_email(msg)
                if code:
                    logger.info(f"🔐 Got verification code for {company or 'Greenhouse'}: {code}")
                    return code
            
            logger.info(f"📭 No recent verification code found for {company or 'any company'}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error reading emails: {e}")
            return None
    
    async def wait_for_verification_code(
        self, 
        company: str = None,
        timeout_seconds: int = MAX_WAIT_SECONDS
    ) -> Optional[str]:
        """
        Wait for verification code email to arrive
        
        Args:
            company: Company name to filter (e.g., "xAI")
            timeout_seconds: How long to wait
        
        Returns:
            str: Verification code or None if timeout
        """
        logger.info(f"⏳ Waiting for Greenhouse verification email (max {timeout_seconds}s)...")
        
        start_time = datetime.now()
        
        while (datetime.now() - start_time).seconds < timeout_seconds:
            code = self.get_latest_greenhouse_code(company, max_age_minutes=5)
            
            if code:
                return code
            
            logger.debug(f"   📭 No code yet, checking again in {CHECK_INTERVAL_SECONDS}s...")
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)
        
        logger.warning(f"⏰ Timeout waiting for verification code ({timeout_seconds}s)")
        return None
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION WITH ATS SUBMITTER
# ═══════════════════════════════════════════════════════════════════════════════

async def handle_greenhouse_verification(
    page,
    company: str,
    email_verifier: GreenhouseEmailVerifier = None
) -> bool:
    """
    Handle Greenhouse email verification flow
    
    Args:
        page: Playwright page object
        company: Company name for filtering emails
        email_verifier: Optional pre-initialized verifier
    
    Returns:
        bool: True if verification successful
    """
    
    # Check if verification is required
    verification_input = await page.query_selector(
        'input[name*="security"], input[placeholder*="security"], input[aria-label*="code"]'
    )
    
    if not verification_input:
        logger.debug("ℹ️ No verification required for this form")
        return True  # No verification needed
    
    logger.info("🔐 Greenhouse email verification required!")
    
    # Get or create email verifier
    if email_verifier is None:
        email_verifier = GreenhouseEmailVerifier()
    
    # Wait for verification code
    code = await email_verifier.wait_for_verification_code(company)
    
    if not code:
        logger.error("❌ Could not get verification code")
        return False
    
    # Enter code into form
    try:
        await verification_input.fill(code)
        logger.info(f"✅ Entered verification code: {code}")
        
        # Click verify/submit button
        verify_button = await page.query_selector(
            'button[type="submit"], button:has-text("Verify"), button:has-text("Submit")'
        )
        if verify_button:
            await verify_button.click()
            await page.wait_for_load_state('networkidle')
            logger.info("✅ Submitted verification code")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error entering verification code: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

async def test_email_verifier():
    """Test the Greenhouse email verifier"""
    print("\n" + "=" * 60)
    print("🧪 TESTING GREENHOUSE EMAIL VERIFIER")
    print("=" * 60 + "\n")
    
    verifier = GreenhouseEmailVerifier()
    
    if not verifier.email_password:
        print("❌ Cannot test: ZOHO_APP_PASSWORD not configured")
        print("\n📝 To configure:")
        print("   1. Go to Zoho Mail → Settings → Security")
        print("   2. Generate an App-specific password")
        print("   3. Set ZOHO_APP_PASSWORD in Railway environment")
        return
    
    with verifier:
        print("📧 Checking for recent Greenhouse verification emails...")
        code = verifier.get_latest_greenhouse_code("xAI", max_age_minutes=60)
        
        if code:
            print(f"✅ Found code: {code}")
        else:
            print("📭 No recent verification codes found")
    
    print("\n✅ Test complete!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_email_verifier())
