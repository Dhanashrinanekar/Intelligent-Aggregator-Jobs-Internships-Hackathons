"""
Backfill script to fix NULL application_start_date and application_end_date
for existing opportunities in the database.
"""

import sys
import os
from datetime import datetime, timedelta

# Add repo root to path
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from database.models import get_db_session, Opportunity

def backfill_null_dates():
    """Update all opportunities with NULL dates."""
    session = get_db_session()

    try:
        # Find opportunities with NULL start dates
        null_start_opps = session.query(Opportunity).filter(
            Opportunity.application_start_date.is_(None)
        ).all()

        if not null_start_opps:
            print("✅ No opportunities with NULL start dates found.")
            return 0

        print(f"📅 Found {len(null_start_opps)} opportunities with NULL dates. Backfilling...")

        updated_count = 0
        for opp in null_start_opps:
            # Use created_at as fallback start date
            start_date = opp.created_at or datetime.utcnow()

            # Set end date 20 days later
            end_date = start_date + timedelta(days=20)

            opp.application_start_date = start_date
            opp.application_end_date = end_date
            opp.updated_at = datetime.utcnow()

            updated_count += 1
            print(f"  ✓ Updated: {opp.role} at {opp.company_name}")

        session.commit()
        print(f"✅ Successfully backfilled dates for {updated_count} opportunities.")
        return updated_count

    except Exception as e:
        session.rollback()
        print(f"❌ Error during backfill: {e}")
        return 0
    finally:
        session.close()

if __name__ == "__main__":
    print("🔧 Starting date backfill...")
    count = backfill_null_dates()
    print(f"📊 Backfill complete. Updated {count} records.")