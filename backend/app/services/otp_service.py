"""OTP Service for Email Verification"""
import random
import string
import socket
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import OTPCode, User
from app.services.email_service import EmailService


class OTPService:
    OTP_EXPIRY_MINUTES = 10

    @staticmethod
    def generate_otp() -> str:
        return ''.join(random.choices(string.digits, k=6))

    @staticmethod
    def is_domain_reachable(email: str) -> bool:
        """
        Check whether the email's domain has a valid DNS entry.
        Returns False for made-up domains like dhanubsbsvb...@gmail.com? No —
        gmail.com IS real. But dhanubsbsvb...@fakexyz123.com would fail here.
        This catches non-existent domains, not non-existent Gmail inboxes.
        """
        try:
            domain = email.strip().lower().split('@')[1]
            # Try to resolve the domain — raises socket.gaierror if domain doesn't exist
            socket.getaddrinfo(domain, None)
            return True
        except (socket.gaierror, IndexError, Exception):
            return False

    @staticmethod
    def send_otp_email(email: str, otp: str) -> bool:
        """Send OTP verification email."""
        email_service = EmailService()

        subject = "Your JobMatch Verification Code"
        body = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:30px 0;">
  <tr><td align="center">
    <table width="480" cellpadding="0" cellspacing="0"
           style="background:#fff;border-radius:8px;overflow:hidden;
                  box-shadow:0 2px 8px rgba(0,0,0,0.1);max-width:480px;width:100%;">

      <tr>
        <td style="background:linear-gradient(135deg,#667eea,#764ba2);padding:28px 36px;text-align:center;">
          <h1 style="margin:0;color:#fff;font-size:22px;">&#10003; Verify your email</h1>
          <p style="margin:6px 0 0;color:rgba(255,255,255,0.8);font-size:13px;">JobMatch account verification</p>
        </td>
      </tr>

      <tr>
        <td style="padding:28px 36px 10px;">
          <p style="margin:0;font-size:15px;color:#333;">Hi there,</p>
          <p style="margin:10px 0 0;font-size:14px;color:#555;">
            Use the code below to verify your email address. It expires in <strong>10 minutes</strong>.
          </p>
        </td>
      </tr>

      <tr>
        <td style="padding:20px 36px;">
          <div style="background:#f0f2ff;border:2px solid #667eea;border-radius:8px;
                      text-align:center;padding:20px;">
            <span style="font-size:36px;font-weight:bold;letter-spacing:10px;
                         color:#667eea;font-family:'Courier New',monospace;">
              {otp}
            </span>
          </div>
        </td>
      </tr>

      <tr>
        <td style="padding:0 36px 28px;">
          <p style="margin:0;font-size:13px;color:#999;text-align:center;">
            Do not share this code with anyone.<br>
            If you didn't request this, please ignore this email.
          </p>
        </td>
      </tr>

      <tr>
        <td style="background:#f8f9fa;padding:16px 36px;text-align:center;border-top:1px solid #eee;">
          <p style="margin:0;font-size:12px;color:#aaa;">&copy; 2024 JobMatch. All rights reserved.</p>
        </td>
      </tr>

    </table>
  </td></tr>
</table>
</body>
</html>
"""
        return email_service.send_email(email, subject, body)

    @staticmethod
    def send_password_reset_email(email: str, otp: str) -> bool:
        """Send password reset OTP email."""
        email_service = EmailService()
        subject = "JobMatch — Password Reset Code"
        reset_link = f"http://localhost:8000/reset-password?email={email}&otp={otp}"

        body = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:30px 0;">
  <tr><td align="center">
    <table width="480" cellpadding="0" cellspacing="0"
           style="background:#fff;border-radius:8px;overflow:hidden;
                  box-shadow:0 2px 8px rgba(0,0,0,0.1);max-width:480px;width:100%;">

      <tr>
        <td style="background:linear-gradient(135deg,#e53935,#c62828);padding:28px 36px;text-align:center;">
          <h1 style="margin:0;color:#fff;font-size:22px;">&#128274; Password Reset</h1>
          <p style="margin:6px 0 0;color:rgba(255,255,255,0.8);font-size:13px;">JobMatch account security</p>
        </td>
      </tr>

      <tr>
        <td style="padding:28px 36px 10px;">
          <p style="margin:0;font-size:15px;color:#333;">Hi,</p>
          <p style="margin:10px 0 0;font-size:14px;color:#555;">
            We received a request to reset your password. Use the code below or click the link.
            This code expires in <strong>10 minutes</strong>.
          </p>
        </td>
      </tr>

      <tr>
        <td style="padding:20px 36px;">
          <div style="background:#fff5f5;border:2px solid #e53935;border-radius:8px;
                      text-align:center;padding:20px;">
            <span style="font-size:36px;font-weight:bold;letter-spacing:10px;
                         color:#e53935;font-family:'Courier New',monospace;">
              {otp}
            </span>
          </div>
        </td>
      </tr>

      <tr>
        <td style="padding:0 36px 8px;text-align:center;">
          <a href="{reset_link}"
             style="display:inline-block;background:#e53935;color:#fff;text-decoration:none;
                    padding:10px 24px;border-radius:5px;font-size:14px;font-weight:bold;">
            Reset my password →
          </a>
        </td>
      </tr>

      <tr>
        <td style="padding:16px 36px 28px;">
          <p style="margin:0;font-size:13px;color:#999;text-align:center;">
            If you didn't request this, your account is safe — just ignore this email.
          </p>
        </td>
      </tr>

      <tr>
        <td style="background:#f8f9fa;padding:16px 36px;text-align:center;border-top:1px solid #eee;">
          <p style="margin:0;font-size:12px;color:#aaa;">&copy; 2024 JobMatch. All rights reserved.</p>
        </td>
      </tr>

    </table>
  </td></tr>
</table>
</body>
</html>
"""
        return email_service.send_email(email, subject, body)

    @staticmethod
    def create_otp(db: Session, email: str, user_id: int = None) -> str:
        """Invalidate old OTPs and create a fresh one."""
        db.query(OTPCode).filter(
            OTPCode.email == email,
            OTPCode.is_used == False
        ).update({"is_used": True})

        otp = OTPService.generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=OTPService.OTP_EXPIRY_MINUTES)

        db.add(OTPCode(
            user_id=user_id,
            email=email,
            otp_code=otp,
            expires_at=expires_at
        ))
        db.commit()
        return otp

    @staticmethod
    def verify_otp(db: Session, email: str, otp: str) -> bool:
        """Return True if OTP is valid and unused, then mark it used."""
        record = db.query(OTPCode).filter(
            OTPCode.email == email,
            OTPCode.otp_code == otp,
            OTPCode.is_used == False,
            OTPCode.expires_at > datetime.utcnow()
        ).first()

        if not record:
            return False

        record.is_used = True
        db.commit()
        return True