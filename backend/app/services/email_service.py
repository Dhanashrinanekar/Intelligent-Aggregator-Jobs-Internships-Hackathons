
"""Email Notification Service"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session
from app.models import User, Opportunity, SimilarityScore, EmailNotification
from app.config import settings
from typing import List

class EmailService:
    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.sender_email = settings.SMTP_EMAIL
        self.sender_password = settings.SMTP_PASSWORD
    
    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Send email via SMTP"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'html'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.send_message(msg)
            server.quit()
            
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    def send_job_match_notification(self, db: Session):
        """Send notifications for new high-scoring matches"""
        # Get matches above threshold that haven't been emailed
        pending = db.query(SimilarityScore).filter(
            SimilarityScore.similarity_score >= 0.3,
            SimilarityScore.email_sent == False
        ).all()
        
        for match in pending:
            user = db.query(User).filter(User.user_id == match.user_id).first()
            job = db.query(Opportunity).filter(Opportunity.id == match.job_id).first()
            
            if not user or not job:
                continue
            
            # Create email body
            subject = f"🎯 New Job Match: {job.role} at {job.company_name}"
            body = f"""
            
            
                Hi {user.name},
                We found a great job match for you!
                
                
                    {job.role}
                    Company: {job.company_name}
                    Type: {job.opportunity_type}
                    Skills Required: {job.skills}
                    Experience: {job.experience_required}
                    Match Score: {float(match.similarity_score):.2%}
                    Portal: {job.job_portal_name}
                
                
                
                    
                        Apply Now
                    
                
                
                
                    This job was matched based on your resume and skills.
                    Match accuracy: {float(match.similarity_score):.2%}
                
            
            
            """
            
            # Send email
            success = self.send_email(user.email, subject, body)
            
            if success:
                # Mark as sent
                match.email_sent = True
                
                # Log notification
                notification = EmailNotification(
                    user_id=user.user_id,
                    job_id=job.id,
                    similarity_score=match.similarity_score,
                    email_status='sent'
                )
                db.add(notification)
            
        db.commit()
        print(f"Sent {len(pending)} email notifications")