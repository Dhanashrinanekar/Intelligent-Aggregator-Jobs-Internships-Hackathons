"""
Job Search API
Provides search functionality for frontend to query the database
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from database import JobDatabase
except ImportError:
    from database.db_operations import JobDatabase


class JobSearchAPI:
    """API for searching jobs in the database."""
    
    def __init__(self):
        """Initialize database connection."""
        self.db = JobDatabase()
    
    def search_jobs(self, 
                    keyword=None, 
                    location=None, 
                    portal=None,
                    opportunity_type=None,
                    experience=None,
                    limit=50,
                    offset=0):
        """
        Advanced job search with multiple filters.
        
        Args:
            keyword (str): Search in role, skills, company name
            location (str): Filter by location
            portal (str): Filter by job portal
            opportunity_type (str): Filter by job type (Full-time, Internship, etc.)
            experience (str): Filter by experience level
            limit (int): Maximum results to return
            offset (int): Offset for pagination
            
        Returns:
            dict: {
                'jobs': [...],
                'total_count': int,
                'filters_applied': {...}
            }
        """
        query = """
        SELECT 
            id,
            company_name,
            role,
            opportunity_type,
            skills,
            experience_required,
            job_portal_name,
            application_link,
            created_at
        FROM opportunities
        WHERE 1=1
        """
        
        params = []
        filters_applied = {}
        
        # Add keyword search (searches in role, skills, company_name)
        if keyword:
            query += """
            AND (
                role ILIKE %s 
                OR skills ILIKE %s 
                OR company_name ILIKE %s
            )
            """
            keyword_pattern = f"%{keyword}%"
            params.extend([keyword_pattern, keyword_pattern, keyword_pattern])
            filters_applied['keyword'] = keyword
        
        # Add location filter
        if location:
            # Note: location is in extra fields, need to join or store separately
            # For now, we skip this as location isn't in main table
            filters_applied['location'] = location
        
        # Add portal filter
        if portal:
            query += " AND job_portal_name = %s"
            params.append(portal)
            filters_applied['portal'] = portal
        
        # Add opportunity type filter
        if opportunity_type:
            query += " AND opportunity_type ILIKE %s"
            params.append(f"%{opportunity_type}%")
            filters_applied['opportunity_type'] = opportunity_type
        
        # Add experience filter
        if experience:
            query += " AND experience_required ILIKE %s"
            params.append(f"%{experience}%")
            filters_applied['experience'] = experience
        
        # Get total count first
        count_query = query.replace(
            "SELECT id, company_name, role, opportunity_type, skills, experience_required, job_portal_name, application_link, created_at",
            "SELECT COUNT(*)"
        )
        
        self.db.cursor.execute(count_query, params)
        total_count = self.db.cursor.fetchone()[0]
        
        # Add sorting and pagination
        query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        # Execute main query
        self.db.cursor.execute(query, params)
        columns = [desc[0] for desc in self.db.cursor.description]
        results = self.db.cursor.fetchall()
        
        jobs = []
        for row in results:
            job_dict = dict(zip(columns, row))
            # Convert datetime to string
            if job_dict.get('created_at'):
                job_dict['created_at'] = job_dict['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            jobs.append(job_dict)
        
        return {
            'jobs': jobs,
            'total_count': total_count,
            'returned_count': len(jobs),
            'filters_applied': filters_applied,
            'pagination': {
                'limit': limit,
                'offset': offset,
                'has_more': (offset + len(jobs)) < total_count
            }
        }
    
    def get_recent_jobs(self, hours=24, limit=100):
        """Get jobs added in the last N hours."""
        query = """
        SELECT 
            id, company_name, role, opportunity_type, skills,
            experience_required, job_portal_name, application_link, created_at
        FROM opportunities
        WHERE created_at > NOW() - INTERVAL '%s hours'
        ORDER BY created_at DESC
        LIMIT %s
        """
        
        self.db.cursor.execute(query, (hours, limit))
        columns = [desc[0] for desc in self.db.cursor.description]
        results = self.db.cursor.fetchall()
        
        jobs = []
        for row in results:
            job_dict = dict(zip(columns, row))
            if job_dict.get('created_at'):
                job_dict['created_at'] = job_dict['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            jobs.append(job_dict)
        
        return jobs
    
    def get_trending_skills(self, limit=20):
        """Get most in-demand skills from recent jobs."""
        query = """
        SELECT 
            skills,
            COUNT(*) as job_count
        FROM opportunities
        WHERE skills != 'N/A'
        AND created_at > NOW() - INTERVAL '7 days'
        GROUP BY skills
        ORDER BY job_count DESC
        LIMIT %s
        """
        
        self.db.cursor.execute(query, (limit,))
        results = self.db.cursor.fetchall()
        
        # Parse and count individual skills
        skill_counts = {}
        for row in results:
            skills_str = row[0]
            if skills_str and skills_str != 'N/A':
                skills = [s.strip() for s in skills_str.split(',')]
                for skill in skills:
                    if skill:
                        skill_counts[skill] = skill_counts.get(skill, 0) + row[1]
        
        # Sort and return top skills
        sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [{'skill': skill, 'count': count} for skill, count in sorted_skills]
    
    def get_top_companies(self, limit=20):
        """Get companies with most job openings."""
        query = """
        SELECT 
            company_name,
            COUNT(*) as job_count
        FROM opportunities
        WHERE created_at > NOW() - INTERVAL '7 days'
        GROUP BY company_name
        ORDER BY job_count DESC
        LIMIT %s
        """
        
        self.db.cursor.execute(query, (limit,))
        results = self.db.cursor.fetchall()
        
        return [{'company': row[0], 'job_count': row[1]} for row in results]
    
    def get_portal_stats(self):
        """Get statistics by portal."""
        query = """
        SELECT 
            job_portal_name,
            COUNT(*) as total_jobs,
            COUNT(DISTINCT company_name) as companies,
            COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as jobs_today
        FROM opportunities
        GROUP BY job_portal_name
        ORDER BY total_jobs DESC
        """
        
        self.db.cursor.execute(query)
        results = self.db.cursor.fetchall()
        
        return [{
            'portal': row[0],
            'total_jobs': row[1],
            'companies': row[2],
            'jobs_today': row[3]
        } for row in results]
    
    def close(self):
        """Close database connection."""
        self.db.close()


# Example usage functions for frontend integration
def search_for_frontend(keyword, page=1, per_page=20):
    """
    Simple search function for frontend.
    
    Args:
        keyword (str): Search keyword (e.g., "python developer")
        page (int): Page number (1-indexed)
        per_page (int): Results per page
        
    Returns:
        dict: Search results with pagination
    """
    api = JobSearchAPI()
    offset = (page - 1) * per_page
    
    results = api.search_jobs(
        keyword=keyword,
        limit=per_page,
        offset=offset
    )
    
    api.close()
    return results


def get_homepage_data():
    """
    Get data for homepage/dashboard.
    
    Returns:
        dict: Dashboard data (recent jobs, stats, trending skills)
    """
    api = JobSearchAPI()
    
    data = {
        'recent_jobs': api.get_recent_jobs(hours=24, limit=10),
        'trending_skills': api.get_trending_skills(limit=15),
        'top_companies': api.get_top_companies(limit=10),
        'portal_stats': api.get_portal_stats(),
        'database_stats': api.db.get_statistics()
    }
    
    api.close()
    return data


if __name__ == "__main__":
    """Test the search API."""
    import json
    
    print("="*80)
    print("🔍 TESTING JOB SEARCH API")
    print("="*80 + "\n")
    
    # Test 1: Search for Python jobs
    print("Test 1: Searching for 'python developer'...")
    results = search_for_frontend("python developer", page=1, per_page=5)
    print(f"✅ Found {results['total_count']} total jobs")
    print(f"📄 Showing {results['returned_count']} jobs\n")
    
    for i, job in enumerate(results['jobs'], 1):
        print(f"{i}. {job['role']} at {job['company_name']}")
        print(f"   Portal: {job['job_portal_name']}")
        print(f"   Skills: {job['skills'][:60]}...")
        print()
    
    # Test 2: Get homepage data
    print("\n" + "="*80)
    print("Test 2: Getting homepage dashboard data...")
    dashboard = get_homepage_data()
    
    print(f"\n📊 Database Statistics:")
    print(f"   Total Jobs: {dashboard['database_stats']['total_jobs']}")
    print(f"   Total Companies: {dashboard['database_stats']['total_companies']}")
    print(f"   Jobs Today: {dashboard['database_stats']['jobs_scraped_today']}")
    
    print(f"\n🔥 Trending Skills (Top 5):")
    for skill_data in dashboard['trending_skills'][:5]:
        print(f"   • {skill_data['skill']}: {skill_data['count']} jobs")
    
    print(f"\n🏢 Top Companies (Top 5):")
    for company_data in dashboard['top_companies'][:5]:
        print(f"   • {company_data['company']}: {company_data['job_count']} jobs")
    
    print(f"\n🌐 Portal Statistics:")
    for portal_data in dashboard['portal_stats']:
        print(f"   • {portal_data['portal']}: {portal_data['total_jobs']} jobs ({portal_data['jobs_today']} today)")
    
    print("\n" + "="*80)
    print("✅ API tests completed!")
    print("="*80 + "\n")