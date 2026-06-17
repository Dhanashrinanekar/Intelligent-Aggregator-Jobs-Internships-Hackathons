"""
One-time migration: backfill NULL created_at values in the opportunities table.

Run once from the backend/ directory:
    python backfill_created_at.py

What it does:
- Sets created_at = NOW() for all rows where created_at IS NULL
- Sets updated_at = NOW() for all rows where updated_at IS NULL
- Safe to run multiple times (only touches NULL rows)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime
from app.database import SessionLocal
from app.models import Opportunity
from sqlalchemy import update

def backfill():
    db = SessionLocal()
    try:
        now = datetime.now()

        # Count nulls before
        null_count = db.query(Opportunity).filter(Opportunity.created_at == None).count()
        print(f"Found {null_count} rows with NULL created_at")

        if null_count == 0:
            print("Nothing to backfill.")
            return

        # Backfill created_at
        result = db.execute(
            update(Opportunity)
            .where(Opportunity.created_at == None)
            .values(created_at=now)
        )
        print(f"Updated created_at for {result.rowcount} rows")

        # Backfill updated_at
        db.execute(
            update(Opportunity)
            .where(Opportunity.updated_at == None)
            .values(updated_at=now)
        )

        db.commit()
        print("✅ Backfill complete. All created_at values are now set.")
        print("   Future jobs will automatically get the correct insert timestamp.")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    backfill()