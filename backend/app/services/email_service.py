"""Email Notification Service"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session
from app.models import User, Opportunity, SimilarityScore, EmailNotification
from app.config import settings


class EmailService:
    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.sender_email = settings.SMTP_EMAIL
        self.sender_password = settings.SMTP_PASSWORD

    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Send a single HTML email via SMTP."""
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = f"JobMatch <{self.sender_email}>"
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
            print(f"❌ Error sending email to {to_email}: {e}")
            return False

    # ------------------------------------------------------------------ #
    #  Weekly digest — top 5 recommendations per user, every Sunday 9 AM  #
    # ------------------------------------------------------------------ #
    def send_weekly_digest(self, db: Session):
        """Send top-5 job recommendations to every user who has a resume."""
        from datetime import datetime

        users = db.query(User).filter(User.resume_file != None).all()
        if not users:
            print("No users with resumes — skipping weekly digest.")
            return

        sent_count = 0

        for user in users:
            # Fetch top-5 matches for this user, ordered by score descending
            top_matches = (
                db.query(SimilarityScore, Opportunity)
                .join(Opportunity, SimilarityScore.job_id == Opportunity.id)
                .filter(SimilarityScore.user_id == user.user_id)
                .filter(SimilarityScore.similarity_score >= 0.30)
                .order_by(SimilarityScore.similarity_score.desc())
                .limit(5)
                .all()
            )

            if not top_matches:
                print(f"  ⚠️  No matches for {user.email} — skipping")
                continue

            subject = f"Your Top {len(top_matches)} Job Picks This Week 🎯"
            body = self._build_digest_email(user.name, top_matches)

            success = self.send_email(user.email, subject, body)
            if success:
                sent_count += 1
                # Log each sent job in EmailNotification
                for score_row, job in top_matches:
                    db.add(EmailNotification(
                        user_id=user.user_id,
                        job_id=job.id,
                        similarity_score=score_row.similarity_score,
                        email_status='sent'
                    ))
                print(f"  ✅ Digest sent to {user.email} ({len(top_matches)} jobs)")
            else:
                print(f"  ❌ Failed to send digest to {user.email}")

        db.commit()
        print(f"\n📧 Weekly digest complete — {sent_count}/{len(users)} emails sent")

    # ------------------------------------------------------------------ #
    #  Instant alert — called right after resume upload (single best match)#
    # ------------------------------------------------------------------ #
    def send_job_match_notification(self, db: Session):
        """Send notification for any unsent match above threshold."""
        NOTIFY_THRESHOLD = 0.3

        pending = (
            db.query(SimilarityScore)
            .filter(
                SimilarityScore.similarity_score >= NOTIFY_THRESHOLD,
                SimilarityScore.email_sent == False,
            )
            .all()
        )

        sent_count = 0
        for match in pending:
            user = db.query(User).filter(User.user_id == match.user_id).first()
            job  = db.query(Opportunity).filter(Opportunity.id == match.job_id).first()
            if not user or not job:
                continue

            match_pct = f"{float(match.similarity_score) * 100:.1f}%"
            subject   = f"New Match: {job.role} at {job.company_name} ({match_pct})"
            body      = self._build_single_match_email(user.name, job, match.similarity_score)

            if self.send_email(user.email, subject, body):
                match.email_sent = True
                db.add(EmailNotification(
                    user_id=user.user_id,
                    job_id=job.id,
                    similarity_score=match.similarity_score,
                    email_status='sent'
                ))
                sent_count += 1

        db.commit()
        print(f"📧 Instant notifications: {sent_count}/{len(pending)} sent")

    # ------------------------------------------------------------------ #
    #  HTML builders                                                       #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _safe(val):
        """Return val if meaningful, else None."""
        if not val:
            return None
        c = val.strip().lower().replace('&nbsp;', '').replace('#', '')
        return val.strip() if c not in ('', 'n/a', 'null', 'not specified', 'na') else None

    def _job_card_html(self, index: int, job: Opportunity, score: float) -> str:
        """Render one job card for the digest email."""
        match_pct   = f"{score * 100:.1f}%"
        skills      = self._safe(job.skills)
        experience  = self._safe(job.experience_required)
        portal      = self._safe(job.job_portal_name)
        opp_type    = job.opportunity_type.capitalize() if job.opportunity_type else ''

        details_rows = ""
        if opp_type:
            details_rows += f'<span style="display:inline-block;background:#e8eaf6;color:#3949ab;padding:3px 10px;border-radius:12px;font-size:12px;margin-right:6px;">{opp_type}</span>'
        if portal:
            details_rows += f'<span style="display:inline-block;background:#e0f2f1;color:#00796b;padding:3px 10px;border-radius:12px;font-size:12px;margin-right:6px;">{portal}</span>'
        if experience:
            details_rows += f'<span style="display:inline-block;background:#fce4ec;color:#c62828;padding:3px 10px;border-radius:12px;font-size:12px;">{experience}</span>'

        skills_row = f'<p style="margin:8px 0 0;font-size:13px;color:#555;"><strong>Skills:</strong> {skills}</p>' if skills else ''

        return f"""
        <tr>
          <td style="padding:0 0 16px 0;">
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="border:1px solid #e8eaf6;border-radius:8px;overflow:hidden;">
              <tr>
                <td style="padding:16px 20px;">
                  <!-- rank + match score -->
                  <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                      <td>
                        <span style="font-size:12px;color:#999;">#{index}</span>
                        <strong style="font-size:16px;color:#1a1a2e;margin-left:6px;">{job.role}</strong>
                      </td>
                      <td align="right">
                        <span style="background:#e8f5e9;color:#2e7d32;padding:4px 10px;border-radius:12px;font-size:13px;font-weight:bold;">{match_pct} match</span>
                      </td>
                    </tr>
                  </table>
                  <!-- company -->
                  <p style="margin:4px 0 8px;font-size:14px;color:#555;">🏢 {job.company_name}</p>
                  <!-- badges -->
                  <div style="margin-bottom:8px;">{details_rows}</div>
                  {skills_row}
                  <!-- apply button -->
                  <div style="margin-top:12px;">
                    <a href="{job.application_link}"
                       style="display:inline-block;background:#667eea;color:#fff;text-decoration:none;
                              padding:8px 20px;border-radius:5px;font-size:13px;font-weight:bold;">
                      Apply Now →
                    </a>
                  </div>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        """

    def _build_digest_email(self, name: str, top_matches: list) -> str:
        from datetime import datetime
        week = datetime.now().strftime("%B %d, %Y")
        cards = "".join(
            self._job_card_html(i + 1, job, score_row.similarity_score)
            for i, (score_row, job) in enumerate(top_matches)
        )

        return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:30px 0;">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0"
           style="background:#fff;border-radius:8px;overflow:hidden;
                  box-shadow:0 2px 8px rgba(0,0,0,0.1);max-width:600px;width:100%;">

      <!-- Header -->
      <tr>
        <td style="background:linear-gradient(135deg,#667eea,#764ba2);padding:28px 40px;text-align:center;">
          <h1 style="margin:0;color:#fff;font-size:22px;">🎯 Your Top {len(top_matches)} Jobs This Week</h1>
          <p style="margin:6px 0 0;color:rgba(255,255,255,0.8);font-size:13px;">Week of {week}</p>
        </td>
      </tr>

      <!-- Greeting -->
      <tr>
        <td style="padding:24px 40px 16px;">
          <p style="margin:0;font-size:15px;color:#333;">Hi <strong>{name}</strong>,</p>
          <p style="margin:8px 0 0;font-size:14px;color:#666;">
            Here are your top {len(top_matches)} job matches based on your resume. Apply before they close!
          </p>
        </td>
      </tr>

      <!-- Job Cards -->
      <tr>
        <td style="padding:0 40px 10px;">
          <table width="100%" cellpadding="0" cellspacing="0">
            {cards}
          </table>
        </td>
      </tr>

      <!-- CTA -->
      <tr>
        <td style="padding:10px 40px 30px;text-align:center;">
          <a href="http://127.0.0.1:8000/recommendations"
             style="display:inline-block;background:linear-gradient(135deg,#667eea,#764ba2);
                    color:#fff;text-decoration:none;padding:12px 32px;
                    border-radius:6px;font-size:14px;font-weight:bold;">
            View All Recommendations →
          </a>
        </td>
      </tr>

      <!-- Footer -->
      <tr>
        <td style="background:#f8f9fa;padding:18px 40px;text-align:center;border-top:1px solid #eee;">
          <p style="margin:0;font-size:12px;color:#aaa;">
            You're receiving this because you have a resume on JobMatch.<br>
            &copy; 2024 JobMatch. All rights reserved.
          </p>
        </td>
      </tr>

    </table>
  </td></tr>
</table>
</body>
</html>
"""

    def _build_single_match_email(self, name: str, job: Opportunity, score: float) -> str:
        match_pct  = f"{score * 100:.1f}%"
        skills     = self._safe(job.skills)
        experience = self._safe(job.experience_required)
        portal     = self._safe(job.job_portal_name)
        opp_type   = job.opportunity_type.capitalize() if job.opportunity_type else ''

        rows = ""
        if opp_type:
            rows += f"<tr><td style='padding:6px 0;color:#888;width:130px;'>Type</td><td style='padding:6px 0;color:#333;'>{opp_type}</td></tr>"
        if skills:
            rows += f"<tr><td style='padding:6px 0;color:#888;'>Skills</td><td style='padding:6px 0;color:#333;'>{skills}</td></tr>"
        if experience:
            rows += f"<tr><td style='padding:6px 0;color:#888;'>Experience</td><td style='padding:6px 0;color:#333;'>{experience}</td></tr>"
        if portal:
            rows += f"<tr><td style='padding:6px 0;color:#888;'>Portal</td><td style='padding:6px 0;color:#333;'>{portal}</td></tr>"

        return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:30px 0;">
  <tr><td align="center">
    <table width="580" cellpadding="0" cellspacing="0"
           style="background:#fff;border-radius:8px;overflow:hidden;
                  box-shadow:0 2px 8px rgba(0,0,0,0.1);max-width:580px;width:100%;">

      <tr>
        <td style="background:linear-gradient(135deg,#667eea,#764ba2);padding:24px 36px;">
          <h1 style="margin:0;color:#fff;font-size:20px;">📌 New Job Match!</h1>
          <p style="margin:4px 0 0;color:rgba(255,255,255,0.8);font-size:13px;">{match_pct} match with your resume</p>
        </td>
      </tr>

      <tr>
        <td style="padding:24px 36px 8px;">
          <p style="margin:0;font-size:15px;color:#333;">Hi <strong>{name}</strong>,</p>
          <p style="margin:8px 0 0;font-size:14px;color:#666;">A new job matches your profile:</p>
        </td>
      </tr>

      <tr>
        <td style="padding:8px 36px 20px;">
          <table width="100%" cellpadding="0" cellspacing="0"
                 style="border:1px solid #e8eaf6;border-radius:6px;padding:16px;">
            <tr>
              <td style="padding-bottom:10px;">
                <strong style="font-size:17px;color:#1a1a2e;">{job.role}</strong><br>
                <span style="font-size:14px;color:#666;">🏢 {job.company_name}</span>
              </td>
            </tr>
            <tr><td><table width="100%" cellpadding="0" cellspacing="0"
                           style="border-top:1px solid #eee;padding-top:8px;">{rows}</table></td></tr>
          </table>
        </td>
      </tr>

      <tr>
        <td style="padding:0 36px 28px;text-align:center;">
          <a href="{job.application_link}"
             style="display:inline-block;background:#667eea;color:#fff;text-decoration:none;
                    padding:11px 30px;border-radius:5px;font-size:14px;font-weight:bold;">
            Apply Now →
          </a>
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