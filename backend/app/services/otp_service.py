"""OTP Service for Email Verification"""
import random
import string
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import OTPCode, User
from app.services.email_service import EmailService

class OTPService:
    """Service to handle OTP generation, sending, and verification"""
    
    OTP_EXPIRY_MINUTES = 10  # OTP valid for 10 minutes
    
    @staticmethod
    def generate_otp():
        """Generate a random 6-digit OTP"""
        return ''.join(random.choices(string.digits, k=6))
    
    @staticmethod
    def send_otp_email(email: str, otp: str) -> bool:
        """Send OTP to user email"""
        email_service = EmailService()
        subject = "Your AI Job Aggregator Verification Code"
        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <div style="max-width: 500px; margin: 0 auto; padding: 20px; background-color: #f8f9fa; border-radius: 8px;">
                    <h2 style="color: #0d6efd; text-align: center;">Email Verification</h2>
                    
                    <p style="color: #333; font-size: 16px;">Hi there,</p>
                    
                    <p style="color: #666; font-size: 14px;">Your email verification code is:</p>
                    
                    <div style="background-color: white; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0; border: 2px solid #0d6efd;">
                        <h1 style="color: #0d6efd; letter-spacing: 5px; font-family: 'Courier New', monospace; margin: 0;">
                            {otp}
                        </h1>
                    </div>
                    
                    <p style="color: #999; font-size: 12px; text-align: center;">
                        This code will expire in 10 minutes. Do not share this code with anyone.
                    </p>
                    
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                    
                    <p style="color: #999; font-size: 12px; text-align: center;">
                        If you didn't request this code, please ignore this email.
                    </p>
                    
                    <p style="color: #999; font-size: 12px; text-align: center;">
                        © 2024 AI Job Aggregator. All rights reserved.
                    </p>
                </div>
            </body>
        </html>
        """
        return email_service.send_email(email, subject, body)

    @staticmethod
    def send_password_reset_email(email: str, otp: str) -> bool:
        """Send password reset instructions with OTP"""
        email_service = EmailService()
        subject = "AI Job Aggregator Password Reset"
        reset_link = f"http://localhost:8000/reset-password?email={email}&otp={otp}"
        body = f"""
        <html>
            <body style=\"font-family: Arial, sans-serif;\">
                <div style=\"max-width: 500px; margin: 0 auto; padding: 20px; background-color: #f8f9fa; border-radius: 8px;\">
                    <h2 style=\"color: #dc3545; text-align: center;\">Password Reset Request</h2>
                    <p style=\"color: #333; font-size: 16px;\">You requested to reset your password. Use the code below or click the link to choose a new password:</p>
                    <div style=\"background-color: white; padding: 15px; border-radius: 8px; margin: 20px 0; border: 1px solid #ced4da; text-align: center;\">
                        <strong style=\"font-size: 18px;\">{otp}</strong>
                    </div>
                    <p style=\"color: #333; font-size: 14px;\">Reset link: <a href=\"{reset_link}\">Reset my password</a></p>
                    <p style=\"color: #999; font-size: 12px;\">This code is valid for 10 minutes. If you did not request this, ignore this email.</p>
                    <p style=\"color: #999; font-size: 12px;\">© 2024 AI Job Aggregator</p>
                </div>
            </body>
        </html>
        """
        return email_service.send_email(email, subject, body)

    @staticmethod
    def create_otp(db: Session, email: str, user_id: int = None) -> str:
        """Create and save OTP to database"""
        # Invalidate previous OTPs for this email
        previous_otps = db.query(OTPCode).filter(
            OTPCode.email == email,
            OTPCode.is_used == False
        ).all()
        
        for prev_otp in previous_otps:
            prev_otp.is_used = True
        
        # Generate new OTP
        otp = OTPService.generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=OTPService.OTP_EXPIRY_MINUTES)
        
        otp_code = OTPCode(
            user_id=user_id,
            email=email,
            otp_code=otp,
            expires_at=expires_at
        )
        
        db.add(otp_code)
        db.commit()
        
        return otp
    
    @staticmethod
    def verify_otp(db: Session, email: str, otp: str) -> bool:
        """Verify if OTP is correct and not expired"""
        otp_record = db.query(OTPCode).filter(
            OTPCode.email == email,
            OTPCode.otp_code == otp,
            OTPCode.is_used == False,
            OTPCode.expires_at > datetime.utcnow()
        ).first()
        
        if not otp_record:
            return False
        
        # Mark as used
        otp_record.is_used = True
        db.commit()
        
        return True
