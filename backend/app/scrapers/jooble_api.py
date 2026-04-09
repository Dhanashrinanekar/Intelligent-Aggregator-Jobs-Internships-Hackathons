import requests
import json
import re
from datetime import datetime
import sys
import os
from typing import List, Dict, Optional
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Ensure repo root is on sys.path so root-level packages resolve correctly
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

# Sometimes this module is imported as part of the backend app package,
# and sometimes it is run from the repository root. Support both paths.
try:
    from app.utils.date_utils import resolve_dates_for_job
except ImportError:
    from utils.date_utils import resolve_dates_for_job


class JoobleJobAggregator:
    """Fetch job listings from Jooble API."""
    
    BASE_URL = "https://jooble.org/api"
    
    def __init__(self, api_key: str):
        """
        Initialize Jooble aggregator with API key.
        
        Args:
            api_key (str): Your Jooble API key from https://jooble.org/api/about
        """
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        print(f"🔑 Jooble API Aggregator initialized")
        print(f"   API Key: {api_key[:10]}...{api_key[-10:]}")
    
    def search_jobs(
        self, 
        keyword: str = "python developer",
        location: str = "",
        num_pages: int = 1,
        save_to_db: bool = True,
        radius: int = 0,
        salary: Optional[int] = None
    ) -> List[Dict]:
        """
        Search for jobs using Jooble API.
        
        Args:
            keyword (str): Job search keyword
            location (str): Job location
            num_pages (int): Number of pages to fetch
            save_to_db (bool): Whether to save to database
            radius (int): Search radius in km (0, 4, 8, 16, 26, 40, 80)
            salary (int): Minimum salary filter
        
        Returns:
            list: List of job dictionaries
        """
        print(f"\n🔍 Searching Jooble for '{keyword}'...")
        if location:
            print(f"📍 Location: {location}")
        if radius:
            print(f"📍 Radius: {radius} km")
        if salary:
            print(f"💰 Minimum Salary: {salary}")
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        jobs = []
        
        for page in range(1, num_pages + 1):
            print(f"\n🌐 Fetching page {page}...")
            
            try:
                jobs_page = self._fetch_page(
                    keyword=keyword,
                    location=location,
                    page=page,
                    radius=radius,
                    salary=salary
                )
                
                if not jobs_page:
                    print(f"⚠️ No jobs found on page {page}")
                    break
                
                print(f"✅ Page {page}: Found {len(jobs_page)} jobs")
                jobs.extend(jobs_page)
                
                # Rate limiting - wait between requests
                if page < num_pages:
                    print(f"⏳ Waiting 1 second before next page...")
                    time.sleep(1)
                
            except Exception as e:
                print(f"⚠️ Error on page {page}: {str(e)}")
                break
        
        print(f"\n{'='*80}")
        print(f"🎯 Fetch Complete!")
        print(f"   Total jobs fetched: {len(jobs)}")
        print(f"   Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")
        
        # Save to database if requested
        if save_to_db and jobs:
            print("💾 Saving to database...")
            try:
                from database.db_operations import JobDatabase
                db = JobDatabase()
                inserted = db.insert_jobs_bulk(jobs)
                db.close()
                print(f"✅ Successfully saved {inserted} jobs to database!")
            except Exception as e:
                print(f"❌ Database save failed: {e}")
        
        return jobs
    
    def _fetch_page(
        self,
        keyword: str,
        location: str,
        page: int = 1,
        radius: int = 0,
        salary: Optional[int] = None
    ) -> List[Dict]:
        """
        Fetch a single page from Jooble API.
        
        Endpoint: POST https://jooble.org/api/{api_Key}
        
        Args:
            keyword (str): Search keyword
            location (str): Location filter
            page (int): Page number (starts from 1)
            radius (int): Search radius
            salary (int): Minimum salary
        
        Returns:
            list: Jobs from this page
        """
        # Build the correct endpoint URL
        url = f"{self.BASE_URL}/{self.api_key}"
        
        # Build payload according to Jooble API documentation
        payload = {
            "keywords": keyword,
            "location": location if location else "India",
            "page": page
        }
        
        # Add optional parameters if provided
        if radius:
            payload["radius"] = str(radius)
        
        if salary:
            payload["salary"] = salary
        
        print(f"   📤 Endpoint: POST {self.BASE_URL}/{self.api_key[:10]}...")
        print(f"   📦 Payload: {json.dumps(payload, indent=6)}")
        
        try:
            response = self.session.post(
                url,
                json=payload,
                timeout=30,
                verify=True
            )
            
            print(f"   📊 Status Code: {response.status_code}")
            
            if response.status_code == 403:
                print(f"   ❌ Access Denied (403): Invalid API Key")
                print(f"   💡 Check your API key at https://jooble.org/api/about")
                return []
            
            if response.status_code == 404:
                print(f"   ❌ Not Found (404): Endpoint or resource not available")
                print(f"   💡 Verify you're using correct endpoint format")
                return []
            
            if response.status_code != 200:
                print(f"   ⚠️ API returned status {response.status_code}")
                print(f"   Response: {response.text[:300]}")
                return []
            
            data = response.json()
            
            # Check for API errors in response
            if "error" in data:
                print(f"   ❌ API Error: {data['error']}")
                return []
            
            total_count = data.get("totalCount", 0)
            jobs_data = data.get("jobs", [])
            
            print(f"   💾 Total available: {total_count} | This page: {len(jobs_data)}")
            
            if not jobs_data:
                return []
            
            # Parse and transform job data
            jobs = []
            for idx, job in enumerate(jobs_data, 1):
                try:
                    job_obj = self._parse_job(job)
                    jobs.append(job_obj)
                    role = job_obj['role'][:35]
                    company = job_obj['company_name'][:25]
                    print(f"  ✓ [{idx}/{len(jobs_data)}] {role:40} @ {company:30}")
                except Exception as e:
                    print(f"  ✗ [{idx}/{len(jobs_data)}] Parse error: {str(e)[:40]}")
                    continue
            
            return jobs
        
        except requests.exceptions.Timeout:
            print(f"   ⏱️ Timeout: API took too long (>30s)")
            return []
        
        except requests.exceptions.ConnectionError as e:
            print(f"   🔌 Connection Error")
            print(f"   Details: {str(e)[:100]}")
            return []
        
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Request Error: {str(e)}")
            return []
        
        except json.JSONDecodeError:
            print(f"   ❌ Invalid JSON response")
            print(f"   Response: {response.text[:200]}")
            return []
        
        except Exception as e:
            print(f"   ❌ Unexpected Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def _extract_skills(self, job_data: Dict) -> str:
        """Extract skills from API response where available."""
        raw_skills = job_data.get("skills")
        if raw_skills:
            if isinstance(raw_skills, list):
                return ", ".join([skill.strip() for skill in raw_skills if skill and skill.strip()]) or "N/A"
            skills_text = str(raw_skills).strip()
            if skills_text:
                return skills_text

        snippet = job_data.get("snippet") or job_data.get("description") or ""
        if isinstance(snippet, str) and snippet.strip():
            parts = [part.strip() for part in re.split(r"[\n·•,;]", snippet) if part.strip()]
            cleaned = []
            for part in parts:
                lower = part.lower()
                if len(part) < 2:
                    continue
                if any(term in lower for term in [
                    "salary", "₹", "rs", "per", "month", "year", "annum", "lpa",
                    "full-time", "part-time", "contract", "temporary", "internship", "freelance",
                    "experience", "location", "apply", "job", "company", "role", "description",
                    "posted", "updated", "date"
                ]):
                    continue
                cleaned.append(part)
            if cleaned:
                return ", ".join(cleaned[:8])

        return "N/A"

    def _extract_experience(self, job_data: Dict) -> str:
        """Extract experience requirements from API response where available."""
        # Check for explicit experience field
        raw_exp = job_data.get("experience") or job_data.get("experience_required")
        if raw_exp:
            exp_text = str(raw_exp).strip()
            if exp_text and exp_text.lower() not in ["n/a", "na", "none", ""]:
                return exp_text

        # Try to extract from snippet/description
        snippet = job_data.get("snippet") or job_data.get("description") or ""
        if isinstance(snippet, str) and snippet.strip():
            lower_snippet = snippet.lower()
            
            # Look for common experience patterns
            exp_patterns = [
                r"(\d+[-\s]*\d*\s*years?\s*experience)",
                r"(experience\s*[:\-]\s*\d+[-\s]*\d*\s*years?)",
                r"(\d+[-\s]*\d*\s*years?\s*of\s*experience)",
                r"(minimum\s*\d+[-\s]*\d*\s*years?)",
                r"(\d+[-\s]*\d*\s*years?\s*required)",
                r"(fresher|entry\s*level|0[-\s]*\d*\s*years?)",
                r"(mid[-\s]*level|senior|experienced)",
            ]
            
            for pattern in exp_patterns:
                match = re.search(pattern, lower_snippet, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
            
            # Look for standalone year mentions that might indicate experience
            year_matches = re.findall(r"(\d+[-\s]*\d*\s*years?)", lower_snippet, re.IGNORECASE)
            if year_matches:
                # Filter out salary-related years
                filtered = []
                for match in year_matches:
                    context = lower_snippet[max(0, lower_snippet.find(match.lower())-20):lower_snippet.find(match.lower())+len(match)+20]
                    if not any(term in context for term in ["salary", "₹", "rs", "per", "month", "year", "annum", "lpa", "package"]):
                        filtered.append(match)
                if filtered:
                    return filtered[0].strip()

        return "N/A"

    def _parse_job(self, job_data: Dict) -> Dict:
        """
        Parse job data from Jooble API response.
        
        Jooble response fields:
        - title: Job title
        - company: Company name
        - location: Job location
        - link: Application link
        - type: Employment type
        - snippet: Job description
        - salary: Salary info
        - source: Source of job
        - updated: Last updated
        - id: Unique ID
        
        Args:
            job_data (dict): Raw job data from API
        
        Returns:
            dict: Transformed job data matching DB schema
        """
        job_obj = {
            "company_name": job_data.get("company", "N/A"),
            "role": job_data.get("title", "N/A"),
            "opportunity_type": job_data.get("type", ""),
            "application_start_date": None,
            "application_end_date": None,
            "skills": self._extract_skills(job_data),
            "experience_required": self._extract_experience(job_data),
            "job_portal_name": "Jooble.org",
            "application_link": job_data.get("link", "N/A"),
            # Extra fields for display
            "location": job_data.get("location", "N/A"),
            "salary": job_data.get("salary", "N/A"),
            "description": job_data.get("snippet", "N/A"),
            "source": job_data.get("source", "N/A"),
            "updated": job_data.get("updated", "N/A"),
            "job_id": job_data.get("id", "N/A"),
            "fetched_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Resolve dates to ensure no NULL values
        resolve_dates_for_job(job_obj)
        
        return job_obj


def save_to_json(jobs: List[Dict], filename: str = "jooble_jobs.json") -> None:
    """Save jobs to JSON file."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved {len(jobs)} jobs to {filename}")


def save_to_csv(jobs: List[Dict], filename: str = "jooble_jobs.csv") -> None:
    """Save jobs to CSV file."""
    import csv
    
    if not jobs:
        print("⚠️ No jobs to save")
        return
    
    keys = jobs[0].keys()
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(jobs)
    print(f"💾 Saved {len(jobs)} jobs to {filename}")


def print_summary(jobs: List[Dict], num_display: int = 5) -> None:
    """Print a formatted summary of fetched jobs."""
    if not jobs:
        print("⚠️ No jobs to display")
        return
    
    print(f"\n{'='*80}")
    print(f"📋 JOB LISTINGS SUMMARY (Showing {min(num_display, len(jobs))} of {len(jobs)})")
    print(f"{'='*80}\n")
    
    for i, job in enumerate(jobs[:num_display], 1):
        print(f"{i}. {job['role']}")
        print(f"   🏢 Company: {job['company_name']}")
        print(f"   📍 Location: {job.get('location', 'N/A')}")
        print(f"   💼 Type: {job.get('opportunity_type', 'N/A')}")
        print(f"   💰 Salary: {job.get('salary', 'N/A')}")
        
        if job.get('description') != "N/A":
            desc = job.get('description', '')
            print(f"   📝 Description: {desc[:100]}..." if len(desc) > 100 else f"   📝 Description: {desc}")
        
        if job.get('updated') != "N/A":
            print(f"   🕐 Updated: {job.get('updated')}")
        
        print(f"   📌 Source: {job.get('source', 'N/A')}")
        print(f"   🔗 Link: {job['application_link']}")
        print()


if __name__ == "__main__":
    # Load API key from .env file
    JOOBLE_API_KEY = os.getenv("JOOBLE_API_KEY")
    
    # Configuration - You can also load these from .env if you want
    KEYWORD = os.getenv("JOOBLE_KEYWORD", "developer")
    LOCATION = os.getenv("JOOBLE_LOCATION", "India")
    NUM_PAGES = int(os.getenv("JOOBLE_NUM_PAGES", "2"))
    RADIUS = int(os.getenv("JOOBLE_RADIUS", "0"))
    MIN_SALARY = None
    SAVE_TO_DB = os.getenv("SAVE_TO_DB", "True").lower() == "true"
    SAVE_FILES = os.getenv("SAVE_FILES", "True").lower() == "true"
    
    # Check if API key is set
    if not JOOBLE_API_KEY:
        print("❌ ERROR: JOOBLE_API_KEY not found in .env file!")
        print("\n📋 Setup Instructions:")
        print("   1. Create/Edit .env file in your project root:")
        print("      C:\\Users\\dhana\\OneDrive\\Desktop\\job-aggregator\\.env")
        print("\n   2. Add these lines to .env:")
        print("      JOOBLE_API_KEY=ff6c1ec8-41f9-410f-9411-c7df15824951")
        print("      JOOBLE_KEYWORD=developer")
        print("      JOOBLE_LOCATION=India")
        print("      JOOBLE_NUM_PAGES=2")
        print("      JOOBLE_RADIUS=0")
        print("      SAVE_TO_DB=True")
        print("      SAVE_FILES=True")
        print("\n   3. Save the .env file")
        print("   4. Run the script again")
        sys.exit(1)
    
    print(f"✅ API Key loaded from .env file")
    
    # Initialize aggregator
    jooble = JoobleJobAggregator(JOOBLE_API_KEY)
    
    # Search jobs
    results = jooble.search_jobs(
        keyword=KEYWORD,
        location=LOCATION,
        num_pages=NUM_PAGES,
        radius=RADIUS,
        salary=MIN_SALARY,
        save_to_db=SAVE_TO_DB
    )
    
    # Display summary
    print_summary(results, num_display=5)
    
    # Save to files
    if results and SAVE_FILES:
        save_to_json(results, "jooble_jobs.json")
        save_to_csv(results, "jooble_jobs.csv")
        print("\nFiles saved!")
    
    if results and SAVE_TO_DB:
        print("Done! Check your PostgreSQL database.")
    elif not results:
        print("\nNo results found. Try different search terms:")
        print("   - JOOBLE_KEYWORD=python")
        print("   - JOOBLE_LOCATION=Remote")
        print("   - JOOBLE_LOCATION=  (leave empty for all)")