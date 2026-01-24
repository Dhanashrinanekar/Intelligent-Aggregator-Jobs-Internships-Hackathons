"""
Scheduler for Daily Job Scraping
Auto-runs comprehensive job scraping at scheduled times
"""

import schedule
import time
from datetime import datetime
import subprocess
import sys
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

# Configuration
SCRAPE_TIME = "02:00"  # 2 AM daily (low traffic time)
SCRAPE_MODE = "tech"  # Options: 'full', 'tech', 'quick'
SEND_EMAIL_REPORTS = False  # Set to True to get email notifications


def send_email_notification(subject, body):
    """Send email notification (optional)."""
    if not SEND_EMAIL_REPORTS:
        return
    
    sender_email = os.getenv("EMAIL_SENDER")
    receiver_email = os.getenv("EMAIL_RECEIVER")
    password = os.getenv("EMAIL_PASSWORD")
    
    if not all([sender_email, receiver_email, password]):
        print("Email credentials not configured")
        return
    
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, password)
        server.send_message(msg)
        server.quit()
        print("Email notification sent")
    except Exception as e:
        print(f"Email failed: {e}")


def run_daily_scraper():
    """Execute the daily scraper."""
    print("\n" + "="*80)
    print("SCHEDULED JOB SCRAPING STARTED")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Mode: {SCRAPE_MODE.upper()}")
    print("="*80 + "\n")
    
    start_time = time.time()
    
    try:
        # Run scraper
        cmd = [sys.executable, "daily_all_jobs_scraper.py", "--mode", SCRAPE_MODE]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10800  # 3 hour timeout
        )
        
        duration = time.time() - start_time
        
        # Save output log
        log_filename = f"scheduler_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        with open(log_filename, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write(f"SCHEDULED RUN: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"MODE: {SCRAPE_MODE}\n")
            f.write(f"DURATION: {duration/60:.1f} minutes\n")
            f.write("="*80 + "\n\n")
            f.write("STDOUT:\n" + result.stdout)
            f.write("\n\nSTDERR:\n" + result.stderr)
        
        if result.returncode == 0:
            print("Scraping completed successfully!")
            print(f"Duration: {duration/60:.1f} minutes")
            print(f"Log: {log_filename}")
            
            # Extract stats from output
            jobs_count = "N/A"
            for line in result.stdout.split('\n'):
                if 'Total Unique Jobs:' in line:
                    jobs_count = line.split(':')[1].strip()
                    break
            
            # Send success email
            if SEND_EMAIL_REPORTS:
                subject = f"Job Scraping Success - {jobs_count} jobs"
                body = f"Job scraping completed successfully.\n\n"
                body += f"Jobs scraped: {jobs_count}\n"
                body += f"Duration: {duration/60:.1f} minutes\n"
                body += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                body += f"See full log: {log_filename}"
                send_email_notification(subject, body)
        else:
            print(f"Scraping failed (return code: {result.returncode})")
            print(f"Error log: {log_filename}")
            
            # Send failure email
            if SEND_EMAIL_REPORTS:
                subject = "Job Scraping Failed"
                body = f"Job scraping failed with errors.\n\n"
                body += f"Return code: {result.returncode}\n"
                body += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                body += f"Error log: {log_filename}\n\n"
                body += f"Last 500 chars of error:\n{result.stderr[-500:]}"
                send_email_notification(subject, body)
        
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        print(f"Timeout after {duration/60:.1f} minutes")
        if SEND_EMAIL_REPORTS:
            send_email_notification(
                "Job Scraping Timeout",
                f"Scraping timed out after {duration/60:.1f} minutes"
            )
    except Exception as e:
        print(f"Error: {e}")
        if SEND_EMAIL_REPORTS:
            send_email_notification("Job Scraping Error", str(e))
    
    print("\n" + "="*80)
    print(f"Next run: {SCRAPE_TIME}")
    print("="*80 + "\n")


def main():
    """Main scheduler loop."""
    print("\n" + "="*80)
    print("DAILY JOB SCRAPER SCHEDULER")
    print("="*80)
    print(f"\nScheduled time: {SCRAPE_TIME} daily")
    print(f"Scraping mode: {SCRAPE_MODE.upper()}")
    print(f"Email reports: {'Enabled' if SEND_EMAIL_REPORTS else 'Disabled'}")
    print(f"Script: daily_all_jobs_scraper.py")
    print(f"Working directory: {os.getcwd()}")
    
    mode_info = {
        'quick': '5 categories (~100-200 jobs, 10-15 min)',
        'tech': '23 tech categories (~400-600 jobs, 30-45 min)',
        'full': '70+ categories (~1000-2000 jobs, 2-3 hours)'
    }
    print(f"Expected: {mode_info.get(SCRAPE_MODE, 'Unknown')}")
    
    print("\nPress Ctrl+C to stop")
    print("="*80 + "\n")
    
    # Schedule the job
    schedule.every().day.at(SCRAPE_TIME).do(run_daily_scraper)
    
    # Optional: Run immediately on start (for testing)
    # print("Running once immediately for testing...\n")
    # run_daily_scraper()
    
    print(f"Scheduler started. Waiting for {SCRAPE_TIME}...\n")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        print("\n\nScheduler stopped by user")
        print("Goodbye!\n")


if __name__ == "__main__":
    # Check dependencies
    try:
        import schedule
    except ImportError:
        print("'schedule' module missing!")
        print("Install: pip install schedule")
        sys.exit(1)
    
    main()
