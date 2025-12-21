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
# Different regions: .com (US), .eu (EU), .in (India), .com.au (Australia)
ZOHO_IMAP_PORT = 993

# All possible Zoho IMAP servers to try (in order of likelihood)
ZOHO_IMAP_SERVERS = [
    os.getenv("ZOHO_IMAP_HOST", "imappro.zoho.com"),  # User-specified or default
    "imappro.zoho.com",   # Pro/Business - US
    "imap.zoho.com",      # Free - US
    "imappro.zoho.eu",    # Pro/Business - EU
    "imap.zoho.eu",       # Free - EU
    "imappro.zoho.in",    # Pro/Business - India
    "imap.zoho.in",       # Free - India
    "imappro.zoho.com.au", # Pro/Business - Australia
    "imap.zoho.com.au",   # Free - Australia
]

# Greenhouse email patterns - multiple possible senders
GREENHOUSE_SENDERS = [
    "no-reply@us.greenhouse-mail.io",
    "no-reply@greenhouse-mail.io",
    "noreply@greenhouse.io",
    "no-reply@greenhouse.io",
    "greenhouse",  # Catch-all for any greenhouse sender
]
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
        raw_password = os.getenv("ZOHO_APP_PASSWORD")  # App-specific password
        
        # Alternative: Use regular password if app password not set
        if not raw_password:
            raw_password = os.getenv("ZOHO_PASSWORD")
        
        # Clean the password - remove any accidental whitespace, quotes, or newlines
        if raw_password:
            original_len = len(raw_password)
            self.email_password = raw_password.strip().strip('"').strip("'").strip()
            cleaned_len = len(self.email_password)
            if original_len != cleaned_len:
                logger.warning(f"⚠️ Password had extra characters! Cleaned: {original_len} → {cleaned_len} chars")
                logger.warning(f"   Removed whitespace/quotes from password")
        else:
            self.email_password = None
        
        self.imap_connection = None
        self._auth_failed = False  # Track if authentication has failed
        self._working_server = None  # Remember which server worked
        
        if not self.email_password:
            logger.warning("⚠️ Zoho email credentials not configured")
            logger.info("   Set ZOHO_APP_PASSWORD or ZOHO_PASSWORD in environment")
        else:
            logger.info("✅ Greenhouse Email Verifier initialized")
            # Zoho app-specific passwords are 12 chars
            pwd_len = len(self.email_password)
            if pwd_len != 12:
                logger.warning(f"⚠️ Password length: {pwd_len} chars (expected 12 for Zoho)")
            else:
                logger.info(f"   Password: {pwd_len} chars ✓")
    
    def connect(self) -> bool:
        """
        Connect to Zoho Mail via IMAP
        
        Tries multiple Zoho servers (different regions and account types)
        until one works.
        
        Returns:
            bool: True if connection successful
        """
        if not self.email_password:
            logger.error("❌ Cannot connect: No Zoho credentials")
            logger.error(f"   ZOHO_EMAIL set: {bool(os.getenv('ZOHO_EMAIL'))}")
            logger.error(f"   ZOHO_APP_PASSWORD set: {bool(os.getenv('ZOHO_APP_PASSWORD'))}")
            return False
        
        logger.info(f"📧 Attempting Zoho Mail connection for: {self.email_address}")
        logger.info(f"🔑 Password length: {len(self.email_password)} chars")
        
        # Try each server until one works
        # Remove duplicates while preserving order
        servers_to_try = list(dict.fromkeys(ZOHO_IMAP_SERVERS))
        
        last_error = None
        auth_errors = []
        
        for server in servers_to_try:
            try:
                logger.info(f"🔌 Trying {server}:{ZOHO_IMAP_PORT}...")
                
                self.imap_connection = imaplib.IMAP4_SSL(server, ZOHO_IMAP_PORT)
                self.imap_connection.login(self.email_address, self.email_password)
                self._auth_failed = False  # Reset auth failure flag on success
                self._working_server = server  # Remember working server
                logger.info(f"✅ Connected to Zoho Mail via {server}")
                return True
                
            except imaplib.IMAP4.error as e:
                error_str = str(e)
                last_error = error_str
                auth_errors.append(f"{server}: {error_str}")
                logger.warning(f"   ❌ {server}: {error_str}")
                # Clean up the connection that's in NONAUTH state
                self.imap_connection = None
                continue
                
            except Exception as e:
                error_str = str(e)
                last_error = error_str
                auth_errors.append(f"{server}: {error_str}")
                logger.warning(f"   ❌ {server}: Connection error - {error_str}")
                self.imap_connection = None
                continue
        
        # All servers failed
        logger.error(f"❌ IMAP login failed on all {len(servers_to_try)} servers")
        logger.error(f"   Email: {self.email_address}")
        logger.error(f"   Password length: {len(self.email_password)} chars")
        logger.error(f"   Password preview: {self.email_password[:3]}***{self.email_password[-2:]}")
        logger.error("")
        logger.error("   Server errors:")
        for err in auth_errors[:3]:  # Show first 3 errors
            logger.error(f"     - {err}")
        logger.error("")
        logger.error("   💡 TROUBLESHOOTING:")
        logger.error("   1. In Railway, check ZOHO_APP_PASSWORD has NO quotes around it")
        logger.error("   2. In Zoho Security settings, check for 'Allowed IPs' restrictions")
        logger.error("   3. Regenerate app password and copy ALL 12 characters")
        logger.error("   4. Verify IMAP checkbox is enabled in Zoho Mail Accounts settings")
        
        # Mark as auth failure - don't retry with same credentials
        self._auth_failed = True
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
        # Don't retry if authentication already failed (wrong credentials)
        if self._auth_failed:
            logger.debug("⏭️ Skipping email check - authentication previously failed")
            return None
            
        if not self.imap_connection:
            if not self.connect():
                return None
        
        try:
            # Check multiple folders (inbox and spam)
            folders_to_check = ["INBOX", "Spam", "Junk", "[Gmail]/Spam"]
            all_email_ids = []
            
            for folder in folders_to_check:
                try:
                    status, _ = self.imap_connection.select(folder)
                    if status != "OK":
                        continue
                    
                    # Search for Greenhouse emails using multiple sender patterns
                    for sender in GREENHOUSE_SENDERS:
                        search_criteria = f'(FROM "{sender}")'
                        status, message_ids = self.imap_connection.search(None, search_criteria)
                        if status == "OK" and message_ids[0]:
                            folder_ids = [(folder, eid) for eid in message_ids[0].split()]
                            all_email_ids.extend(folder_ids)
                    
                    # Also search by subject containing "security code"
                    search_criteria = '(SUBJECT "security code")'
                    status, message_ids = self.imap_connection.search(None, search_criteria)
                    if status == "OK" and message_ids[0]:
                        folder_ids = [(folder, eid) for eid in message_ids[0].split()]
                        all_email_ids.extend(folder_ids)
                        
                except Exception as e:
                    logger.debug(f"Could not check folder {folder}: {e}")
                    continue
            
            if not all_email_ids:
                logger.info("📭 No Greenhouse verification emails found")
                return None
            
            # Remove duplicates while preserving order
            seen = set()
            unique_emails = []
            for item in all_email_ids:
                if item not in seen:
                    seen.add(item)
                    unique_emails.append(item)
            
            logger.info(f"📧 Found {len(unique_emails)} potential verification emails")
            
            # Check emails from newest to oldest
            for folder, email_id in reversed(unique_emails[-10:]):
                try:
                    self.imap_connection.select(folder)
                    status, msg_data = self.imap_connection.fetch(email_id, "(RFC822)")
                    
                    if status != "OK":
                        continue
                    
                    msg = email.message_from_bytes(msg_data[0][1])
                    
                    # Check subject
                    subject = decode_header(msg["Subject"])[0][0]
                    if isinstance(subject, bytes):
                        subject = subject.decode('utf-8', errors='ignore')
                    
                    # Must contain security code or verification
                    if "security code" not in subject.lower() and "verification" not in subject.lower():
                        continue
                    
                    # Check if company matches (if specified)
                    if company and company.lower() not in subject.lower():
                        continue
                    
                    # Check email date
                    date_str = msg.get("Date", "")
                    try:
                        email_date = email.utils.parsedate_to_datetime(date_str)
                        age = datetime.now(email_date.tzinfo) - email_date
                        
                        if age > timedelta(minutes=max_age_minutes):
                            logger.debug(f"📧 Email too old: {age}")
                            continue
                    except Exception:
                        pass
                    
                    # Extract code
                    code = self._extract_code_from_email(msg)
                    if code:
                        logger.info(f"🔐 Got verification code for {company or 'Greenhouse'}: {code}")
                        return code
                        
                except Exception as e:
                    logger.debug(f"Error checking email: {e}")
                    continue
            
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
        
        # First attempt to connect - fail early if credentials are wrong
        if not self.imap_connection and not self._auth_failed:
            if not self.connect():
                if self._auth_failed:
                    logger.error("❌ Cannot check for verification code - email authentication failed")
                    logger.error("   Please configure ZOHO_APP_PASSWORD with a valid App-specific password")
                    return None
        
        # If auth already failed, don't keep trying
        if self._auth_failed:
            logger.error("❌ Cannot check for verification code - email credentials are invalid")
            return None
        
        start_time = datetime.now()
        
        while (datetime.now() - start_time).seconds < timeout_seconds:
            code = self.get_latest_greenhouse_code(company, max_age_minutes=5)
            
            if code:
                return code
            
            # Check if authentication failed during the code check
            if self._auth_failed:
                logger.error("❌ Email authentication failed - stopping wait")
                return None
            
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
