import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime, timezone, timedelta
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Make sure the project root is on the path so we can import date_utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.app.utils.date_utils import resolve_dates_for_job


class JobDatabase:
    """Handle all database operations for job aggregator."""

    def __init__(self):
        self.conn = None
        self.cursor = None
        self.connect()

    def connect(self):
        try:
            self.conn = psycopg2.connect(
                host=os.getenv("DB_HOST", "localhost"),
                database=os.getenv("DB_NAME", "job_aggregator"),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", "your_password"),
                port=os.getenv("DB_PORT", "5432"),
            )
            self.cursor = self.conn.cursor()
            print("✅ Connected to PostgreSQL database")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            raise

    def verify_table(self):
        verify_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'opportunities'
        );
        """
        try:
            self.cursor.execute(verify_query)
            exists = self.cursor.fetchone()[0]
            if exists:
                print("✅ 'opportunities' table found")
                return True
            else:
                print("❌ 'opportunities' table not found")
                return False
        except Exception as e:
            print(f"❌ Error verifying table: {e}")
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _prepare_job(job_data: dict) -> dict:
        """
        Resolve date fields so neither is NULL.

        application_start_date:
            API start date  →  posted_date  →  now (UTC)

        application_end_date:
            API expiry date (validThrough / deadline / …)
            → start_date + 20 days

        ✅ FIX: location, salary, description now use `or "N/A"` instead of
        setdefault() — this handles None, empty string AND missing keys,
        whereas setdefault() only handles missing keys.
        """
        # Ensure a fallback posted timestamp exists so start/end dates can be derived.
        if not job_data.get('scraped_at') and not job_data.get('fetched_at') and not job_data.get('posted_date'):
            job_data['scraped_at'] = datetime.now(timezone.utc)
        elif not job_data.get('scraped_at') and job_data.get('fetched_at'):
            job_data['scraped_at'] = job_data['fetched_at']

        resolve_dates_for_job(job_data)   # mutates in-place

        # Hard safety net – should never trigger, but guarantees no NULLs
        now = datetime.now(timezone.utc)
        if job_data.get("application_start_date") is None:
            job_data["application_start_date"] = now
        if job_data.get("application_end_date") is None:
            job_data["application_end_date"] = now + timedelta(days=20)

        # Set defaults for required fields
        job_data.setdefault("opportunity_type", "Full-time")
        job_data.setdefault("skills", "N/A")
        job_data.setdefault("experience_required", "N/A")

        # ✅ FIX: Use `or "N/A"` instead of setdefault()
        # Reason: setdefault() only fills in the key if it's MISSING entirely.
        #         If the scraper passes location=None or location="", setdefault()
        #         does nothing and NULL gets stored in the DB.
        #         `or "N/A"` catches None, "", 0, False — all falsy values.
        job_data["location"]    = job_data.get("location")    or "N/A"
        job_data["salary"]      = job_data.get("salary")      or "N/A"
        job_data["description"] = job_data.get("description") or "N/A"

        return job_data

    # ------------------------------------------------------------------
    # Fix existing NULL rows in the database (run once)
    # ------------------------------------------------------------------

    def fix_null_fields(self) -> int:
        """
        ✅ NEW METHOD: One-time fix to update existing rows that have NULL
        in location, salary, or description columns.

        Run this once after deploying the fix to clean up historical data.

        Returns the number of rows updated.
        """
        fix_query = """
        UPDATE opportunities
        SET
            location    = COALESCE(NULLIF(TRIM(location), ''),    'N/A'),
            salary      = COALESCE(NULLIF(TRIM(salary), ''),      'N/A'),
            description = COALESCE(NULLIF(TRIM(description), ''), 'N/A')
        WHERE
            location    IS NULL OR location    = ''
            OR salary      IS NULL OR salary      = ''
            OR description IS NULL OR description = '';
        """
        try:
            self.cursor.execute(fix_query)
            updated_count = self.cursor.rowcount
            self.conn.commit()
            print(f"✅ Fixed {updated_count} rows — NULL location/salary/description set to 'N/A'")
            return updated_count
        except Exception as e:
            print(f"❌ Error fixing NULL fields: {e}")
            self.conn.rollback()
            return 0

    # ------------------------------------------------------------------
    # Insert
    # ------------------------------------------------------------------

    def insert_job(self, job_data: dict):
        """
        Insert a single job.

        Date resolution rules (no NULL allowed):
          - application_start_date = api_start OR posted_date OR now
          - application_end_date   = api_expiry OR start_date + 20 days

        location / salary / description: scraper value OR "N/A" (never NULL)

        Returns new row id, or None if duplicate / error.
        """
        insert_query = """
        INSERT INTO opportunities (
            company_name,
            role,
            opportunity_type,
            application_start_date,
            application_end_date,
            skills,
            experience_required,
            job_portal_name,
            application_link,
            location,
            salary,
            description
        ) VALUES (
            %(company_name)s,
            %(role)s,
            %(opportunity_type)s,
            %(application_start_date)s,
            %(application_end_date)s,
            %(skills)s,
            %(experience_required)s,
            %(job_portal_name)s,
            %(application_link)s,
            %(location)s,
            %(salary)s,
            %(description)s
        )
        ON CONFLICT (application_link) DO UPDATE SET
            company_name           = EXCLUDED.company_name,
            role                   = EXCLUDED.role,
            opportunity_type       = EXCLUDED.opportunity_type,
            application_start_date = EXCLUDED.application_start_date,
            application_end_date   = EXCLUDED.application_end_date,
            skills                 = EXCLUDED.skills,
            experience_required    = EXCLUDED.experience_required,
            job_portal_name        = EXCLUDED.job_portal_name,
            location               = EXCLUDED.location,
            salary                 = EXCLUDED.salary,
            description            = EXCLUDED.description,
            updated_at             = CURRENT_TIMESTAMP
        RETURNING id;
        """
        try:
            prepared = self._prepare_job(dict(job_data))
            self.cursor.execute(insert_query, prepared)
            row = self.cursor.fetchone()
            self.conn.commit()
            return row[0] if row else None

        except psycopg2.IntegrityError:
            self.conn.rollback()
            return None
        except Exception as e:
            print(f"❌ Error inserting job '{job_data.get('role', 'Unknown')}': {e}")
            self.conn.rollback()
            return None

    def insert_jobs_bulk(self, jobs_list: list) -> int:
        """Insert multiple jobs. Returns count of inserted rows."""
        if not jobs_list:
            print("⚠️ No jobs to insert")
            return 0

        inserted_count = 0
        skipped_count = 0

        print(f"\n💾 Inserting {len(jobs_list)} jobs into database...")

        for idx, job in enumerate(jobs_list, 1):
            job_id = self.insert_job(job)
            if job_id:
                inserted_count += 1
                # ✅ Show location, salary, description in success message
                location_info = (job.get('location') or 'N/A')[:30]
                salary_info   = (job.get('salary')   or 'N/A')[:20]
                print(
                    f"  ✓ [{idx}/{len(jobs_list)}] Inserted: "
                    f"{job.get('role', 'Unknown')} @ {location_info} | 💰 {salary_info}"
                )
            else:
                skipped_count += 1
                print(f"  ⏭️  [{idx}/{len(jobs_list)}] Skipped (duplicate): {job.get('role', 'Unknown')}")

        print(f"\n📊 Database Insert Summary:")
        print(f"   ✅ Inserted:             {inserted_count} jobs")
        print(f"   ⏭️  Skipped (duplicates): {skipped_count} jobs")
        print(f"   📝 Total processed:      {len(jobs_list)} jobs")

        return inserted_count

    # ------------------------------------------------------------------
    # Delete expired jobs
    # ------------------------------------------------------------------

    def delete_expired_jobs(self) -> int:
        """
        Delete all jobs whose application_end_date has passed.

        Also removes dependent rows from:
            similarity_score, email_notifications, job_vector

        Returns the number of opportunity rows deleted.
        """
        now = datetime.now(timezone.utc)

        try:
            self.cursor.execute(
                """
                SELECT id FROM opportunities
                WHERE application_end_date IS NOT NULL
                  AND application_end_date < %s
                """,
                (now,),
            )
            expired_ids = [row[0] for row in self.cursor.fetchall()]

            if not expired_ids:
                print(
                    f"✅ [{now.strftime('%Y-%m-%d %H:%M:%S')}] "
                    "No expired jobs found."
                )
                return 0

            print(
                f"\n🗑️  [{now.strftime('%Y-%m-%d %H:%M:%S')}] "
                f"Removing {len(expired_ids)} expired job(s)..."
            )

            # Delete dependent rows first (FK-safe even with CASCADE)
            for table, fk_col in [
                ("similarity_score",    "job_id"),
                ("email_notifications", "job_id"),
                ("job_vector",          "job_id"),
            ]:
                self.cursor.execute(
                    f"DELETE FROM {table} WHERE {fk_col} = ANY(%s)",
                    (expired_ids,),
                )
                cnt = self.cursor.rowcount
                if cnt:
                    print(f"   • {cnt} row(s) removed from '{table}'")

            # Delete the expired opportunities
            self.cursor.execute(
                "DELETE FROM opportunities WHERE id = ANY(%s)",
                (expired_ids,),
            )
            deleted_count = self.cursor.rowcount
            self.conn.commit()

            print(
                f"✅ Cleanup complete — {deleted_count} expired job(s) deleted."
            )
            return deleted_count

        except Exception as e:
            print(f"❌ Error deleting expired jobs: {e}")
            self.conn.rollback()
            return 0

    # Backward-compatible alias
    def delete_old_jobs(self, days: int = 30) -> int:
        """Delete jobs whose created_at is older than *days* days."""
        query = """
        DELETE FROM opportunities
        WHERE created_at < NOW() - INTERVAL '%s days'
        RETURNING id;
        """
        try:
            self.cursor.execute(query, (days,))
            deleted = self.cursor.rowcount
            self.conn.commit()
            print(f"✅ Deleted {deleted} old jobs (older than {days} days)")
            return deleted
        except Exception as e:
            print(f"❌ Error deleting old jobs: {e}")
            self.conn.rollback()
            return 0

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def get_all_jobs(self, limit: int = 100) -> list:
        query = """
        SELECT * FROM opportunities
        ORDER BY created_at DESC
        LIMIT %s;
        """
        try:
            self.cursor.execute(query, (limit,))
            columns = [desc[0] for desc in self.cursor.description]
            return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        except Exception as e:
            print(f"❌ Error retrieving jobs: {e}")
            return []

    def get_jobs_by_portal(self, portal_name: str) -> list:
        query = """
        SELECT * FROM opportunities
        WHERE job_portal_name = %s
        ORDER BY created_at DESC;
        """
        try:
            self.cursor.execute(query, (portal_name,))
            columns = [desc[0] for desc in self.cursor.description]
            return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        except Exception as e:
            print(f"❌ Error retrieving jobs: {e}")
            return []

    def search_jobs(self, keyword: str, location=None) -> list:
        query = """
        SELECT * FROM opportunities
        WHERE (role ILIKE %s OR skills ILIKE %s)
        ORDER BY created_at DESC;
        """
        try:
            self.cursor.execute(query, [f"%{keyword}%", f"%{keyword}%"])
            columns = [desc[0] for desc in self.cursor.description]
            return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        except Exception as e:
            print(f"❌ Error searching jobs: {e}")
            return []

    def get_statistics(self) -> dict:
        stats_query = """
        SELECT
            COUNT(*)                                                         AS total_jobs,
            COUNT(DISTINCT company_name)                                     AS total_companies,
            COUNT(DISTINCT job_portal_name)                                  AS total_portals,
            COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') AS jobs_today,
            COUNT(*) FILTER (WHERE application_end_date < NOW())             AS expired_jobs,
            -- ✅ NEW: Count how many rows still have NULL/N/A in these columns
            COUNT(*) FILTER (WHERE location    IS NULL OR location    = 'N/A') AS missing_location,
            COUNT(*) FILTER (WHERE salary      IS NULL OR salary      = 'N/A') AS missing_salary,
            COUNT(*) FILTER (WHERE description IS NULL OR description = 'N/A') AS missing_description
        FROM opportunities;
        """
        try:
            self.cursor.execute(stats_query)
            result = self.cursor.fetchone()
            return {
                "total_jobs":           result[0],
                "total_companies":      result[1],
                "total_portals":        result[2],
                "jobs_scraped_today":   result[3],
                "expired_jobs":         result[4],
                "missing_location":     result[5],   # ✅ NEW
                "missing_salary":       result[6],   # ✅ NEW
                "missing_description":  result[7],   # ✅ NEW
            }
        except Exception as e:
            print(f"❌ Error getting statistics: {e}")
            return {}

    def get_recent_jobs(self, hours: int = 24, limit: int = 50) -> list:
        query = """
        SELECT * FROM opportunities
        WHERE created_at > NOW() - INTERVAL '%s hours'
        ORDER BY created_at DESC
        LIMIT %s;
        """
        try:
            self.cursor.execute(query, (hours, limit))
            columns = [desc[0] for desc in self.cursor.description]
            return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        except Exception as e:
            print(f"❌ Error retrieving recent jobs: {e}")
            return []

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("✅ Database connection closed")


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

def save_jobs_to_db(jobs_list: list) -> int:
    db = JobDatabase()
    count = db.insert_jobs_bulk(jobs_list)
    db.close()
    return count


def cleanup_expired_jobs() -> int:
    """Standalone helper: delete all expired jobs, return count removed."""
    db = JobDatabase()
    count = db.delete_expired_jobs()
    db.close()
    return count


# ✅ NEW: Standalone helper to fix existing NULL rows (run once after deploy)
def fix_existing_null_fields() -> int:
    """
    One-time migration helper.
    Updates all existing rows that have NULL in location / salary / description.

    Usage:
        python job_database.py --fix-nulls
    OR import and call directly:
        from job_database import fix_existing_null_fields
        fix_existing_null_fields()
    """
    db = JobDatabase()
    count = db.fix_null_fields()
    db.close()
    return count


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Job Database Utility")
    parser.add_argument(
        "--fix-nulls",
        action="store_true",
        help="Fix existing NULL location/salary/description rows (run once after deploy)",
    )
    args = parser.parse_args()

    print("🔧 Testing Database Connection...\n")
    db = JobDatabase()

    # ✅ NEW: --fix-nulls flag runs the one-time migration
    if args.fix_nulls:
        print("\n🔄 Running one-time NULL field fix...")
        removed = db.fix_null_fields()
        print(f"✅ Fixed {removed} rows.")
        db.close()
        exit(0)

    if db.verify_table():
        stats = db.get_statistics()
        print(f"\n📊 Database Statistics:")
        print(f"   Total Jobs:           {stats.get('total_jobs', 0)}")
        print(f"   Total Companies:      {stats.get('total_companies', 0)}")
        print(f"   Total Portals:        {stats.get('total_portals', 0)}")
        print(f"   Jobs Today:           {stats.get('jobs_scraped_today', 0)}")
        print(f"   Expired Jobs:         {stats.get('expired_jobs', 0)}")
        # ✅ NEW: Show data quality stats
        print(f"\n📋 Data Quality:")
        print(f"   Missing Location:     {stats.get('missing_location', 0)}")
        print(f"   Missing Salary:       {stats.get('missing_salary', 0)}")
        print(f"   Missing Description:  {stats.get('missing_description', 0)}")

        # Clean up expired jobs on every run
        removed = db.delete_expired_jobs()
        print(f"\n🗑️  Removed {removed} expired job(s) from database.")

        recent = db.get_recent_jobs(hours=24, limit=5)
        if recent:
            print(f"\n📋 Recent Jobs (Last 24 hours):")
            for job in recent:
                end         = job.get("application_end_date", "N/A")
                location    = job.get("location",    "N/A")
                salary      = job.get("salary",      "N/A")
                description = job.get("description", "N/A")
                print(f"   • {job['role']} @ {job['company_name']}")
                print(f"     📍 {location}")
                print(f"     💰 {salary}")
                print(f"     📝 {description[:80]}{'...' if len(str(description)) > 80 else ''}")
                print(f"     🗓️  Ends: {end}")

    db.close()
    print("\n✅ Database test completed!")