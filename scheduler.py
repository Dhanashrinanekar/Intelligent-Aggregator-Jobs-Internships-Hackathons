import schedule
import time
from datetime import datetime
from main import main

def job():
    """
    Job to run on schedule
    """
    print("\n" + "🕐 " + "="*58)
    print(f"   Scheduled run started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")
    
    try:
        main()
    except Exception as e:
        print(f"❌ Scheduled job failed: {e}")
    
    print("\n" + "="*60)
    print(f"   Next run scheduled for: {schedule.next_run()}")
    print("="*60 + "\n")


def run_scheduler():
    """
    Run the scheduler
    """
    print("🚀 Job Aggregator Scheduler Started!")
    print("="*60)
    print("📅 Schedule: Daily at 09:00 AM")
    print("⏸️  Press Ctrl+C to stop")
    print("="*60 + "\n")
    
    # Schedule the job to run daily at 9:00 AM
    schedule.every().day.at("09:00").do(job)
    
    # For testing: Run every 5 minutes
    # schedule.every(5).minutes.do(job)
    
    # For testing: Run every hour
    # schedule.every().hour.do(job)
    
    print(f"⏰ Next run: {schedule.next_run()}\n")
    
    # Run immediately on start (optional)
    print("🏃 Running initial job now...\n")
    job()
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == "__main__":
    try:
        run_scheduler()
    except KeyboardInterrupt:
        print("\n\n⚠️  Scheduler stopped by user")
        print("👋 Goodbye!")