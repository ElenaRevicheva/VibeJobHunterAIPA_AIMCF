"""
Email Integration Service for VibeJobHunter
Supports multiple providers: Resend, SendGrid, Gmail API
"""

import os
from typing import Optional, Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """
    Multi-provider email service for job applications
    
    Supported providers:
    1. Resend (recommended - easiest to set up)
    2. SendGrid (enterprise option)
    3. Gmail API (requires OAuth setup)
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
                logger.warning(" RESEND_API_KEY not set")
                return
            
            resend.api_key = api_key
            self.client = resend
            logger.info(" Resend email service initialized")
            
        except ImportError:
            logger.error(" Resend not installed. Install with: pip install resend")
    
    def _init_sendgrid(self):
        """Initialize SendGrid client"""
        try:
            from sendgrid import SendGridAPIClient
            
            api_key = os.getenv('SENDGRID_API_KEY')
            if not api_key:
                logger.warning(" SENDGRID_API_KEY not set")
                return
            
            self.client = SendGridAPIClient(api_key)
            logger.info(" SendGrid email service initialized")
            
        except ImportError:
            logger.error(" SendGrid not installed. Install with: pip install sendgrid")
    
    def _init_gmail(self):
        """Initialize Gmail API client"""
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            
            creds_file = os.getenv('GMAIL_CREDENTIALS_FILE', 'gmail_credentials.json')
            
            if not os.path.exists(creds_file):
                logger.warning(" Gmail credentials file not found")
                return
            
            creds = Credentials.from_authorized_user_file(creds_file)
            self.client = build('gmail', 'v1', credentials=creds)
            logger.info(" Gmail API service initialized")
            
        except ImportError:
            logger.error(" Google API client not installed")
    
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        from_email: Optional[str] = None,
        html: bool = True,
        attachments: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Send an email using configured provider
        
        Args:
            to: Recipient email
            subject: Email subject
            body: Email body (HTML or plain text)
            from_email: Sender email (defaults to configured sender)
            html: Whether body is HTML
            attachments: List of attachment dicts
        
        Returns:
            Dict with 'success', 'message_id', and optional 'error'
        """
        if not self.client:
            return {
                'success': False,
                'error': f'{self.provider} not configured'
            }
        
        try:
            if self.provider == "resend":
                return await self._send_resend(to, subject, body, from_email, html, attachments)
            elif self.provider == "sendgrid":
                return await self._send_sendgrid(to, subject, body, from_email, html, attachments)
            elif self.provider == "gmail":
                return await self._send_gmail(to, subject, body, html, attachments)
        
        except Exception as e:
            logger.error(f" Email send failed: {e}")
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
            from_email = os.getenv('FROM_EMAIL', 'aipa@aideazz.xyz')
        
        params = {
            "from": from_email,
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
            from_email = os.getenv('FROM_EMAIL', 'aipa@aideazz.xyz')
        
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
        """Send a job application email with standard formatting"""
        
        subject = f"Application for {role} at {company}"
        
        html_body = f"""
<!DOCTYPE html>
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
        {cover_letter.replace('\n', '<br>')}
    </div>
    
    <div class="signature">
        <p>Best regards,<br>
        Elena Revicheva<br>
        <a href="mailto:aipa@aideazz.xyz">aipa@aideazz.xyz</a><br>
        <a href="https://linkedin.com/in/elenarevicheva">linkedin.com/in/elenarevicheva</a><br>
        <a href="https://aideazz.xyz">aideazz.xyz</a></p>
    </div>
</body>
</html>
"""
        
        attachments = [resume_attachment] if resume_attachment else None
        
        result = await self.send_email(
            to=to,
            subject=subject,
            body=html_body,
            html=True,
            attachments=attachments
        )
        
        if result['success']:
            logger.info(f" Application sent to {company}: {result['message_id']}")
        else:
            logger.error(f" Failed to send application to {company}: {result.get('error')}")
        
        return result
    
    def test_connection(self) -> bool:
        """Test if email service is properly configured"""
        if not self.client:
            logger.error(f" {self.provider} not configured")
            return False
        
        logger.info(f" {self.provider} configured and ready")
        return True


def create_email_service(provider: str = None) -> EmailService:
    """Create email service instance"""
    if provider:
        return EmailService(provider)
    
    if os.getenv('RESEND_API_KEY'):
        return EmailService('resend')
    elif os.getenv('SENDGRID_API_KEY'):
        return EmailService('sendgrid')
    elif os.path.exists('gmail_credentials.json'):
        return EmailService('gmail')
    else:
        logger.warning(" No email provider configured")
        return EmailService('resend')


if __name__ == '__main__':
    print(" Testing email service...")
    service = create_email_service()
    
    if service.test_connection():
        print(" Email service ready!")
    else:
        print("\n Email service not configured. Set up:")
        print("1. RESEND_API_KEY (recommended)")
        print("2. SENDGRID_API_KEY")
        print("3. Gmail credentials")
