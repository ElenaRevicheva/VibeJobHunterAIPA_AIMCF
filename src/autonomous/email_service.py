"""
Email Integration Service for VibeJobHunter
Supports multiple providers: Resend, SendGrid, Gmail API

🚨 PHASE 1: EMERGENCY FIX + DUAL-TRACK FOUNDATION
- Blocks careers@ emails from Resend (stops bouncing)
- Validates emails before sending
- Adds dual-track routing logic
- Preserves all existing functionality
"""

import os
from typing import Optional, Dict, List
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)


# =============================================================================
# EMERGENCY FIX: EMAIL VALIDATION RULES
# =============================================================================

BLOCKED_EMAIL_PATTERNS = [
    'careers@',
    'jobs@',
    'hr@',
    'recruiting@',
    'talent@',
    'apply@',
    'applications@'
]

ALLOWED_FOUNDER_PATTERNS = [
    r'^[a-z]+@',              # firstname@company.com
    r'^[a-z]+\.[a-z]+@',      # firstname.lastname@company.com
    r'^founder@',
    r'^ceo@',
    r'^hello@',               # Only for small startups
    r'^contact@'              # Only if verified human-monitored
]


def validate_email_for_resend(email: str) -> Dict:
    """
    🚨 CRITICAL: Validates if email should be sent via Resend
    
    Returns:
        {
            'allowed': bool,
            'reason': str,
            'email_type': 'ats' | 'founder' | 'blocked',
            'suggested_action': str
        }
    """
    email_lower = email.lower()
    
    # Check 1: Block ATS/generic emails
    for blocked_pattern in BLOCKED_EMAIL_PATTERNS:
        if blocked_pattern in email_lower:
            logger.warning(f"🚫 BLOCKED: {email} matches pattern '{blocked_pattern}'")
            logger.info(f"   → This should go through ATS submission instead")
            return {
                'allowed': False,
                'reason': f'Blocked pattern: {blocked_pattern}',
                'email_type': 'ats',
                'suggested_action': 'use_ats_api_or_portal',
                'email': email
            }
    
    # Check 2: Validate founder/personal email patterns
    is_founder_pattern = any(
        re.match(pattern, email_lower) 
        for pattern in ALLOWED_FOUNDER_PATTERNS
    )
    
    if not is_founder_pattern:
        logger.warning(f"⚠️ SUSPICIOUS: {email} doesn't match founder patterns")
        logger.info(f"   → Verify this is a real person's email")
        return {
            'allowed': False,
            'reason': 'Does not match founder/executive pattern',
            'email_type': 'unknown',
            'suggested_action': 'verify_email_is_personal',
            'email': email
        }
    
    # Passed validation
    logger.info(f"✅ VALIDATED: {email} is allowed for Resend")
    return {
        'allowed': True,
        'reason': 'Valid founder/executive email pattern',
        'email_type': 'founder',
        'suggested_action': 'proceed_with_founder_outreach',
        'email': email
    }


def should_use_dual_track(job_data: Dict) -> bool:
    """
    Determines if job qualifies for dual-track (ATS + Founder)
    
    Args:
        job_data: Dict with keys: score, seniority, company_size, founder_email
    
    Returns:
        bool: True if job should use dual-track approach
    """
    criteria = {
        'high_score': job_data.get('score', 0) >= 65,
        'senior_role': job_data.get('seniority') in ['senior', 'staff', 'principal', 'lead', 'director', 'vp'],
        'has_founder_email': job_data.get('founder_email') is not None,
        'email_verified': job_data.get('founder_email_verified', False),
        'not_too_big': job_data.get('company_size', 0) < 5000
    }
    
    # All criteria must be met
    qualifies = all(criteria.values())
    
    if qualifies:
        logger.info(f"✅ Job qualifies for DUAL-TRACK approach")
    else:
        failed = [k for k, v in criteria.items() if not v]
        logger.info(f"ℹ️ Job uses ATS-ONLY (failed: {', '.join(failed)})")
    
    return qualifies


# =============================================================================
# EMAIL SERVICE CLASS
# =============================================================================

class EmailService:
    """
    Multi-provider email service for job applications
    
    Supported providers:
    1. Resend (recommended - easiest to set up)
    2. SendGrid (enterprise option)
    3. Gmail API (requires OAuth setup)
    
    🚨 NEW: Built-in validation to prevent careers@ emails
    """
    
    def __init__(self, provider: str = "resend"):
        self.provider = provider.lower()
        self.client = None
        
        if self.provider == "resend":
            self._init_resend()
        elif self.provider == "sendgrid":
            self._init_sendgrid()
        elif self.provider == "gmail":
            self._init_gmail()
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def _init_resend(self):
        """Initialize Resend client"""
        try:
            import resend
            
            api_key = os.getenv('RESEND_API_KEY')
            if not api_key:
                logger.warning("⚠️ RESEND_API_KEY not set")
                return
            
            resend.api_key = api_key
            self.client = resend
            logger.info("✅ Resend email service initialized")
            
        except ImportError:
            logger.error("❌ Resend not installed. Install with: pip install resend")
    
    def _init_sendgrid(self):
        """Initialize SendGrid client"""
        try:
            from sendgrid import SendGridAPIClient
            
            api_key = os.getenv('SENDGRID_API_KEY')
            if not api_key:
                logger.warning("⚠️ SENDGRID_API_KEY not set")
                return
            
            self.client = SendGridAPIClient(api_key)
            logger.info("✅ SendGrid email service initialized")
            
        except ImportError:
            logger.error("❌ SendGrid not installed. Install with: pip install sendgrid")
    
    def _init_gmail(self):
        """Initialize Gmail API client"""
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            
            creds_file = os.getenv('GMAIL_CREDENTIALS_FILE', 'gmail_credentials.json')
            
            if not os.path.exists(creds_file):
                logger.warning("⚠️ Gmail credentials file not found")
                return
            
            creds = Credentials.from_authorized_user_file(creds_file)
            self.client = build('gmail', 'v1', credentials=creds)
            logger.info("✅ Gmail API service initialized")
            
        except ImportError:
            logger.error("❌ Google API client not installed")
    
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        from_email: Optional[str] = None,
        html: bool = True,
        attachments: Optional[List[Dict]] = None,
        skip_validation: bool = False  # 🆕 Emergency override
    ) -> Dict:
        """
        Send an email using configured provider
        
        🚨 NEW: Validates recipient email before sending
        
        Args:
            to: Recipient email
            subject: Email subject
            body: Email body (HTML or plain text)
            from_email: Sender email (defaults to configured sender)
            html: Whether body is HTML
            attachments: List of attachment dicts
            skip_validation: Skip email validation (use carefully!)
        
        Returns:
            Dict with 'success', 'message_id', 'validation', and optional 'error'
        """
        # 🚨 CRITICAL: Validate email BEFORE sending
        if not skip_validation:
            validation = validate_email_for_resend(to)
            
            if not validation['allowed']:
                logger.error(f"🚫 Email send BLOCKED: {to}")
                logger.error(f"   Reason: {validation['reason']}")
                logger.error(f"   Suggested action: {validation['suggested_action']}")
                
                return {
                    'success': False,
                    'blocked': True,
                    'validation': validation,
                    'error': f"Email blocked: {validation['reason']}"
                }
        
        if not self.client:
            return {
                'success': False,
                'error': f'{self.provider} not configured'
            }
        
        try:
            if self.provider == "resend":
                result = await self._send_resend(to, subject, body, from_email, html, attachments)
            elif self.provider == "sendgrid":
                result = await self._send_sendgrid(to, subject, body, from_email, html, attachments)
            elif self.provider == "gmail":
                result = await self._send_gmail(to, subject, body, html, attachments)
            
            # Add validation info to result
            if not skip_validation:
                result['validation'] = validation
            
            return result
        
        except Exception as e:
            logger.error(f"❌ Email send failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _send_resend(
        self,
        to: str,
        subject: str,
        body: str,
        from_email: Optional[str],
        html: bool,
        attachments: Optional[List[Dict]]
    ) -> Dict:
        """Send email via Resend"""
        
        if not from_email:
            # Use verified domain email - replies go to Zoho inbox
            from_email = os.getenv('FROM_EMAIL', 'Elena Revicheva <aipa@aideazz.xyz>')
        
        params = {
            "from": from_email,
            "reply_to": "aipa@aideazz.xyz",  # Ensure replies go to Zoho inbox
            "to": [to],
            "subject": subject,
        }
        
        if html:
            params["html"] = body
        else:
            params["text"] = body
        
        if attachments:
            params["attachments"] = attachments
        
        response = self.client.Emails.send(params)
        
        return {
            'success': True,
            'message_id': response.get('id'),
            'provider': 'resend'
        }
    
    async def _send_sendgrid(
        self,
        to: str,
        subject: str,
        body: str,
        from_email: Optional[str],
        html: bool,
        attachments: Optional[List[Dict]]
    ) -> Dict:
        """Send email via SendGrid"""
        from sendgrid.helpers.mail import Mail, Attachment
        import base64
        
        if not from_email:
            from_email = os.getenv('FROM_EMAIL', 'elena.revicheva2016@gmail.com')
        
        message = Mail(
            from_email=from_email,
            to_emails=to,
            subject=subject,
            html_content=body if html else None,
            plain_text_content=body if not html else None
        )
        
        if attachments:
            for att in attachments:
                encoded = base64.b64encode(att['content']).decode()
                attachment = Attachment(
                    file_content=encoded,
                    file_name=att['filename'],
                    file_type=att.get('type', 'application/pdf')
                )
                message.add_attachment(attachment)
        
        response = self.client.send(message)
        
        return {
            'success': response.status_code in [200, 202],
            'message_id': response.headers.get('X-Message-Id'),
            'provider': 'sendgrid'
        }
    
    async def _send_gmail(
        self,
        to: str,
        subject: str,
        body: str,
        html: bool,
        attachments: Optional[List[Dict]]
    ) -> Dict:
        """Send email via Gmail API"""
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.mime.base import MIMEBase
        from email import encoders
        import base64
        
        if attachments:
            message = MIMEMultipart()
        else:
            message = MIMEText(body, 'html' if html else 'plain')
        
        message['to'] = to
        message['subject'] = subject
        
        if attachments:
            message.attach(MIMEText(body, 'html' if html else 'plain'))
            
            for att in attachments:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(att['content'])
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename={att["filename"]}')
                message.attach(part)
        
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        send_message = self.client.users().messages().send(
            userId='me',
            body={'raw': raw}
        ).execute()
        
        return {
            'success': True,
            'message_id': send_message['id'],
            'provider': 'gmail'
        }
    
    async def send_application_email(
        self,
        to: str,
        company: str,
        role: str,
        cover_letter: str,
        resume_attachment: Optional[Dict] = None
    ) -> Dict:
        """
        Send a job application email with standard formatting
        
        🚨 NEW: Validates recipient before sending
        ⚠️ IMPORTANT: This should ONLY be used for founder outreach emails,
                      NOT for ATS submissions (which should use proper APIs)
        """
        
        # 🚨 VALIDATE: Check if this is an ATS email that should be blocked
        validation = validate_email_for_resend(to)
        
        if not validation['allowed']:
            logger.error(f"🚫 Application email BLOCKED to {to}")
            logger.error(f"   Company: {company}, Role: {role}")
            logger.error(f"   Reason: {validation['reason']}")
            logger.info(f"   ✅ Use ATS submission API instead")
            
            return {
                'success': False,
                'blocked': True,
                'validation': validation,
                'company': company,
                'role': role,
                'error': f"Cannot send to {validation['email_type']} address via Resend"
            }
        
        # Passed validation - proceed with sending
        logger.info(f"✅ Sending application to FOUNDER email: {to}")
        
        subject = f"Application for {role} at {company}"
        
        # Convert newlines to <br> tags OUTSIDE f-string
        cover_letter_html = cover_letter.replace('\n', '<br>')
        
        # Build HTML template without backslashes in f-string
        html_body = f"""<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .header {{ margin-bottom: 20px; }}
        .content {{ margin: 20px 0; }}
        .signature {{ margin-top: 30px; border-top: 1px solid #ddd; padding-top: 20px; }}
    </style>
</head>
<body>
    <div class="header">
        <p>Dear Hiring Manager,</p>
    </div>
    
    <div class="content">
        {cover_letter_html}
    </div>
    
    <div class="signature">
        <p>Best regards,<br>
        Elena Revicheva<br>
        <a href="mailto:aipa@aideazz.xyz">aipa@aideazz.xyz</a><br>
        <a href="https://linkedin.com/in/elenarevicheva">linkedin.com/in/elenarevicheva</a><br>
        <a href="https://aideazz.xyz">aideazz.xyz</a></p>
    </div>
</body>
</html>"""
        
        attachments = [resume_attachment] if resume_attachment else None
        
        result = await self.send_email(
            to=to,
            subject=subject,
            body=html_body,
            html=True,
            attachments=attachments,
            skip_validation=True  # Already validated above
        )
        
        if result['success']:
            logger.info(f"✅ Application sent to {company}: {result['message_id']}")
        else:
            logger.error(f"❌ Failed to send application to {company}: {result.get('error')}")
        
        return result
    
    def test_connection(self) -> bool:
        """Test if email service is properly configured"""
        if not self.client:
            logger.error(f"❌ {self.provider} not configured")
            return False
        
        logger.info(f"✅ {self.provider} configured and ready")
        return True


def create_email_service(provider: str = None) -> EmailService:
    """Create email service instance"""
    if provider:
        return EmailService(provider)
    
    # Auto-detect available provider
    if os.getenv('RESEND_API_KEY'):
        return EmailService('resend')
    elif os.getenv('SENDGRID_API_KEY'):
        return EmailService('sendgrid')
    elif os.path.exists('gmail_credentials.json'):
        return EmailService('gmail')
    else:
        logger.warning("⚠️ No email provider configured")
        return EmailService('resend')  # Default to Resend


# =============================================================================
# STANDALONE TEST
# =============================================================================
if __name__ == '__main__':
    import asyncio
    
    async def test_email_validation():
        """Test email validation logic"""
        print("\n🧪 Testing email validation...")
        print("=" * 60)
        
        test_cases = [
            # Should BLOCK (ATS emails)
            ('careers@webflow.com', False, 'ats'),
            ('jobs@gitlab.com', False, 'ats'),
            ('hr@vercel.com', False, 'ats'),
            ('recruiting@stripe.com', False, 'ats'),
            
            # Should ALLOW (founder/personal emails)
            ('sid@gitlab.com', True, 'founder'),
            ('guillermo@vercel.com', True, 'founder'),
            ('elena@company.com', True, 'founder'),
            ('john.doe@startup.com', True, 'founder'),
            ('hello@smallstartup.com', True, 'founder'),
        ]
        
        print("\n📋 Test Results:")
        for email, should_allow, expected_type in test_cases:
            result = validate_email_for_resend(email)
            
            status = "✅" if result['allowed'] == should_allow else "❌"
            print(f"{status} {email:30} | Allowed: {result['allowed']:5} | Type: {result['email_type']}")
            
            if result['allowed'] != should_allow:
                print(f"   ERROR: Expected allowed={should_allow}, got {result['allowed']}")
        
        print("=" * 60)
    
    async def test_email_service():
        """Test email service configuration"""
        print("\n🧪 Testing email service...")
        print("=" * 60)
        
        service = create_email_service()
        
        if service.test_connection():
            print("✅ Email service ready!")
            print(f"📧 Provider: {service.provider}")
            
            # Test validation integration
            print("\n📧 Testing send with validation:")
            
            # This should be BLOCKED
            result = await service.send_application_email(
                to="careers@testcompany.com",
                company="TestCompany",
                role="Software Engineer",
                cover_letter="This should be blocked"
            )
            print(f"careers@ email: {result}")
            
            # This should be ALLOWED (but won't actually send in test)
            # Uncomment to test real sending
            # result = await service.send_application_email(
            #     to="founder@testcompany.com",
            #     company="TestCompany",
            #     role="Software Engineer",
            #     cover_letter="This should go through"
            # )
            # print(f"founder@ email: {result}")
            
        else:
            print("\n❌ Email service not configured. Set up one of:")
            print("   1. RESEND_API_KEY (recommended)")
            print("   2. SENDGRID_API_KEY")
            print("   3. Gmail credentials (gmail_credentials.json)")
            print("\nGet Resend API key: https://resend.com/api-keys")
        
        print("=" * 60)
    
    async def main():
        await test_email_validation()
        await test_email_service()
    
    asyncio.run(main())