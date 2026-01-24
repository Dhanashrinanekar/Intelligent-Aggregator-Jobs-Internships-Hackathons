import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class JobDatabase:
    """Handle all database operations for job aggregator."""
    
    def __init__(self):
        """Initialize database connection."""
        self.conn = None
        self.cursor = None
        self.connect()
    
    def connect(self):
        """Connect to PostgreSQL database."""
        try:
            self.conn = psycopg2.connect(
                host=os.getenv("DB_HOST", "localhost"),
                database=os.getenv("DB_NAME", "job_aggregator"),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", "your_password"),
                port=os.getenv("DB_PORT", "5432")
            )
            self.cursor = self.conn.cursor()
            print("✅ Connected to PostgreSQL database")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            raise
    
    def verify_table(self):
        """Verify that the opportunities table exists."""
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
    
    def insert_job(self, job_data):
        """
        Insert a single job into the opportunities table.
        Skips if job with same application_link already exists.
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
            application_link
        ) VALUES (
            %(company_name)s, 
            %(role)s, 
            %(opportunity_type)s,
            %(application_start_date)s,
            %(application_end_date)s,
            %(skills)s, 
            %(experience_required)s, 
            %(job_portal_name)s, 
            %(application_link)s
        )
        ON CONFLICT (application_link) DO UPDATE SET
            updated_at = CURRENT_TIMESTAMP
        RETURNING id;
        """
        
        try:
            # Set default values for date fields if not present
            job_data.setdefault('application_start_date', None)
            job_data.setdefault('application_end_date', None)
            
            # Ensure required fields are present
            job_data.setdefault('opportunity_type', 'Full-time')
            job_data.setdefault('skills', 'N/A')
            job_data.setdefault('experience_required', 'N/A')
            
            self.cursor.execute(insert_query, job_data)
            job_id = self.cursor.fetchone()
            self.conn.commit()
            return job_id[0] if job_id else None
        except psycopg2.IntegrityError:
            # Duplicate entry (conflict on application_link)
            self.conn.rollback()
            return None
        except Exception as e:
            print(f"❌ Error inserting job '{job_data.get('role', 'Unknown')}': {e}")
            self.conn.rollback()
            return None
    
    def insert_jobs_bulk(self, jobs_list):
        """
        Insert multiple jobs at once.
        Returns count of newly inserted jobs.
        """
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
                print(f"  ✓ [{idx}/{len(jobs_list)}] Inserted: {job.get('role', 'Unknown')}")
            else:
                skipped_count += 1
                print(f"  ⏭️  [{idx}/{len(jobs_list)}] Skipped (duplicate): {job.get('role', 'Unknown')}")
        
        print(f"\n📊 Database Insert Summary:")
        print(f"   ✅ Inserted: {inserted_count} jobs")
        print(f"   ⏭️  Skipped (duplicates): {skipped_count} jobs")
        print(f"   📝 Total processed: {len(jobs_list)} jobs")
        
        return inserted_count
    
    def get_all_jobs(self, limit=100):
        """Retrieve all jobs from database."""
        query = """
        SELECT * FROM opportunities 
        ORDER BY created_at DESC 
        LIMIT %s;
        """
        
        try:
            self.cursor.execute(query, (limit,))
            columns = [desc[0] for desc in self.cursor.description]
            results = self.cursor.fetchall()
            
            jobs = []
            for row in results:
                jobs.append(dict(zip(columns, row)))
            
            return jobs
        except Exception as e:
            print(f"❌ Error retrieving jobs: {e}")
            return []
    
    def get_jobs_by_portal(self, portal_name):
        """Get jobs from a specific portal."""
        query = """
        SELECT * FROM opportunities 
        WHERE job_portal_name = %s 
        ORDER BY created_at DESC;
        """
        
        try:
            self.cursor.execute(query, (portal_name,))
            columns = [desc[0] for desc in self.cursor.description]
            results = self.cursor.fetchall()
            
            jobs = []
            for row in results:
                jobs.append(dict(zip(columns, row)))
            
            return jobs
        except Exception as e:
            print(f"❌ Error retrieving jobs: {e}")
            return []
    
    def search_jobs(self, keyword, location=None):
        """Search jobs by keyword and optional location."""
        query = """
        SELECT * FROM opportunities 
        WHERE (role ILIKE %s OR skills ILIKE %s)
        """
        params = [f"%{keyword}%", f"%{keyword}%"]
        
        query += " ORDER BY created_at DESC;"
        
        try:
            self.cursor.execute(query, params)
            columns = [desc[0] for desc in self.cursor.description]
            results = self.cursor.fetchall()
            
            jobs = []
            for row in results:
                jobs.append(dict(zip(columns, row)))
            
            return jobs
        except Exception as e:
            print(f"❌ Error searching jobs: {e}")
            return []
    
    def get_statistics(self):
        """Get database statistics."""
        stats_query = """
        SELECT 
            COUNT(*) as total_jobs,
            COUNT(DISTINCT company_name) as total_companies,
            COUNT(DISTINCT job_portal_name) as total_portals,
            COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as jobs_today
        FROM opportunities;
        """
        
        try:
            self.cursor.execute(stats_query)
            result = self.cursor.fetchone()
            
            return {
                "total_jobs": result[0],
                "total_companies": result[1],
                "total_portals": result[2],
                "jobs_scraped_today": result[3]
            }
        except Exception as e:
            print(f"❌ Error getting statistics: {e}")
            return {}
    
    def delete_old_jobs(self, days=30):
        """Delete jobs older than specified days."""
        query = """
        DELETE FROM opportunities 
        WHERE created_at < NOW() - INTERVAL '%s days'
        RETURNING id;
        """
        
        try:
            self.cursor.execute(query, (days,))
            deleted = self.cursor.rowcount
            self.conn.commit()
            print(f"✅ Deleted {deleted} old jobs")
            return deleted
        except Exception as e:
            print(f"❌ Error deleting old jobs: {e}")
            self.conn.rollback()
            return 0
    
    def get_recent_jobs(self, hours=24, limit=50):
        """Get jobs added in the last N hours."""
        query = """
        SELECT * FROM opportunities 
        WHERE created_at > NOW() - INTERVAL '%s hours'
        ORDER BY created_at DESC
        LIMIT %s;
        """
        
        try:
            self.cursor.execute(query, (hours, limit))
            columns = [desc[0] for desc in self.cursor.description]
            results = self.cursor.fetchall()
            
            jobs = []
            for row in results:
                jobs.append(dict(zip(columns, row)))
            
            return jobs
        except Exception as e:
            print(f"❌ Error retrieving recent jobs: {e}")
            return []
    
    def close(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("✅ Database connection closed")


# Convenience functions
def save_jobs_to_db(jobs_list):
    """Quick function to save jobs to database."""
    db = JobDatabase()
    count = db.insert_jobs_bulk(jobs_list)
    db.close()
    return count


if __name__ == "__main__":
    # Test database connection and setup
    print("🔧 Testing Database Connection...\n")
    
    db = JobDatabase()
    
    # Verify table exists
    if db.verify_table():
        # Get statistics
        stats = db.get_statistics()
        print(f"\n📊 Database Statistics:")
        print(f"   Total Jobs: {stats.get('total_jobs', 0)}")
        print(f"   Total Companies: {stats.get('total_companies', 0)}")
        print(f"   Total Portals: {stats.get('total_portals', 0)}")
        print(f"   Jobs Today: {stats.get('jobs_scraped_today', 0)}")
        
        # Show recent jobs
        recent = db.get_recent_jobs(hours=24, limit=5)
        if recent:
            print(f"\n📋 Recent Jobs (Last 24 hours):")
            for job in recent:
                print(f"   • {job['role']} at {job['company_name']} ({job['job_portal_name']})")
    
    db.close()
    print("\n✅ Database test completed!")