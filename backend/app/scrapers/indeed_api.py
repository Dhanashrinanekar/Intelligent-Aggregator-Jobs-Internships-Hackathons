import requests
import os
import sys
from datetime import datetime

# Ensure repo root is on sys.path so root-level packages resolve correctly
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from app.utils.date_utils import resolve_dates_for_job
except ImportError:
    from utils.date_utils import resolve_dates_for_job

def fetch_indeed_jobs(query="python developer", location="India", num_results=10):
    """
    Fetch jobs from Indeed using RapidAPI or similar service
    Note: Indeed doesn't have a free official API. 
    You'll need to use a third-party API service like:
    - RapidAPI's Indeed API
    - SerpAPI
    - ScraperAPI
    
    This is a template - you need to sign up for an API key
    """
    print(f"🔍 Fetching jobs from Indeed API for '{query}'...")
    
    # Example using RapidAPI (you need to sign up at rapidapi.com)
    # Search for "Indeed API" on RapidAPI and get your key
    
    # Placeholder - Replace with actual API
    API_KEY = os.getenv("RAPIDAPI_KEY", "your_rapidapi_key_here")
    
    url = "https://indeed-indeed.p.rapidapi.com/apisearch"
    
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "indeed-indeed.p.rapidapi.com"
    }
    
    params = {
        "q": query,
        "l": location,
        "radius": "25"
    }
    
    jobs = []
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Parse response (structure depends on API)
            results = data.get('results', [])
            
            for item in results[:num_results]:
                job_data = {
                    'company_name': item.get('company', 'N/A'),
                    'role': item.get('jobtitle', 'N/A'),
                    'opportunity_type': 'job',
                    'application_start_date': None,
                    'application_end_date': None,
                    'skills': item.get('snippet', 'N/A'),  # Description snippet
                    'experience_required': 'N/A',
                    'job_portal_name': 'Indeed',
                    'application_link': item.get('url', 'N/A'),
                    'fetched_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # Resolve dates to ensure no NULL values
                resolve_dates_for_job(job_data)
                
                jobs.append(job_data)
            
            print(f"✅ Fetched {len(jobs)} jobs from Indeed")
        else:
            print(f"❌ API Error: {response.status_code}")
    
    except Exception as e:
        print(f"❌ Error fetching from Indeed API: {e}")
    
    return jobs


# Alternative: Simple Indeed scraper (no API needed)
def scrape_indeed_simple(keyword="python developer", location="India"):
    """
    Simple Indeed scraper without API
    Note: Indeed actively blocks scrapers, use with caution
    """
    print(f"🔍 Scraping Indeed for '{keyword}'...")
    
    from bs4 import BeautifulSoup
    
    jobs = []
    url = f"https://www.indeed.co.in/jobs?q={keyword.replace(' ', '+')}&l={location}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find job cards
        job_cards = soup.find_all('div', class_='job_seen_beacon')
        
        for card in job_cards[:10]:  # Limit to 10
            try:
                title_elem = card.find('h2', class_='jobTitle')
                title = title_elem.text.strip() if title_elem else "N/A"
                
                company_elem = card.find('span', class_='companyName')
                company = company_elem.text.strip() if company_elem else "N/A"
                
                link_elem = card.find('a')
                link = "https://www.indeed.co.in" + link_elem['href'] if link_elem else "N/A"
                
                job_data = {
                    'company_name': company,
                    'role': title,
                    'opportunity_type': 'job',
                    'application_start_date': None,
                    'application_end_date': None,
                    'skills': 'N/A',
                    'experience_required': 'N/A',
                    'job_portal_name': 'Indeed',
                    'application_link': link,
                    'fetched_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # Resolve dates to ensure no NULL values
                resolve_dates_for_job(job_data)
                
                jobs.append(job_data)
                
            except Exception as e:
                continue
        
        print(f"✅ Scraped {len(jobs)} jobs from Indeed")
        
    except Exception as e:
        print(f"❌ Error scraping Indeed: {e}")
    
    return jobs


if __name__ == "__main__":
    # Test
    jobs = scrape_indeed_simple("python developer")
    for job in jobs[:3]:
        print(job)