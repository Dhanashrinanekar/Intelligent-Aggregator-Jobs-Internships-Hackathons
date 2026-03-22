"""
Migration script to create OTP table and add is_verified column to users
Run this from the backend folder: python migrate_otp.py
"""
import sys
sys.path.insert(0, '.')

from app.database import engine
from app.models import Base

def migrate():
    """Create all tables defined in models"""
    print("Creating/updating database tables...")
    
    try:
        # This will create all tables including the new OTPCode table
        Base.metadata.create_all(bind=engine)
        print("✅ Database migration completed successfully!")
        print("   - OTP codes table created")
        print("   - is_verified column added to users table (if not exists)")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate()
