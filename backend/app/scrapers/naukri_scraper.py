from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import random
import json
from datetime import datetime
import sys
import os

# Add parent directory to path to import database module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from database.db_operations import JobDatabase  # Import only when needed


def scrape_naukri(keyword="python developer", location="", num_pages=1, save_to_db=True):
    """
    Scrape Naukri.com for job listings.
    
    Args:
        keyword (str): Job search keyword
        location (str): Job location (leave empty for all India)
        num_pages (int): Number of pages to scrape (recommended: 1-3)
        save_to_db (bool): Whether to save to database
    
    Returns:
        list: List of job dictionaries
    """
    print(f"🔍 Scraping Naukri.com for '{keyword}'...")
    if location:
        print(f"📍 Location: {location}")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Configure Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    # Initialize driver
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), 
        options=chrome_options
    )
    
    # Hide webdriver property
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    jobs = []

    for page in range(1, num_pages + 1):
        # Naukri URL structure
        if location:
            url = f"https://www.naukri.com/{keyword.replace(' ', '-')}-jobs-in-{location.replace(' ', '-')}?k={keyword.replace(' ', '%20')}&l={location.replace(' ', '%20')}&page={page}"
        else:
            url = f"https://www.naukri.com/{keyword.replace(' ', '-')}-jobs?k={keyword.replace(' ', '%20')}&page={page}"
        
        print(f"\n🌐 Loading page {page}...")
        print(f"   URL: {url}")
        
        try:
            driver.get(url)
            
            # Wait for job cards to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "srp-jobtuple-wrapper"))
            )
            time.sleep(random.uniform(4, 6))
            
        except Exception as e:
            print(f"⚠️ Timeout on page {page} - Naukri may be rate limiting")
            print(f"   Error: {str(e)[:100]}")
            # Save debug info
            with open(f"debug_naukri_page_{page}.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print(f"📄 Saved page source for debugging")
            break

        # Find all job cards
        job_cards = driver.find_elements(By.CLASS_NAME, "srp-jobtuple-wrapper")
        
        if not job_cards:
            print(f"⚠️ No jobs found on page {page}")
            break

        print(f"✅ Page {page}: Found {len(job_cards)} jobs")

        for idx, card in enumerate(job_cards, 1):
            try:
                # Extract job title
                try:
                    title_elem = card.find_element(By.CLASS_NAME, "title")
                    role = title_elem.text.strip()
                except:
                    continue  # Skip if no title
                
                # Extract company name
                try:
                    company_elem = card.find_element(By.CLASS_NAME, "comp-name")
                    company = company_elem.text.strip()
                except:
                    company = "N/A"
                
                # Extract job link
                try:
                    link_elem = card.find_element(By.CLASS_NAME, "title")
                    link = link_elem.get_attribute("href")
                    if not link:
                        link_elem = card.find_element(By.CSS_SELECTOR, "a.title")
                        link = link_elem.get_attribute("href")
                except:
                    link = "N/A"
                
                # Extract experience
                experience = "N/A"
                try:
                    exp_elem = card.find_element(By.CLASS_NAME, "expwdth")
                    experience = exp_elem.text.strip()
                except:
                    pass
                
                # Extract salary
                salary = "N/A"
                try:
                    salary_elem = card.find_element(By.CLASS_NAME, "sal")
                    salary = salary_elem.text.strip()
                except:
                    pass
                
                # Extract location
                job_location = "N/A"
                try:
                    location_elem = card.find_element(By.CLASS_NAME, "locWdth")
                    job_location = location_elem.text.strip()
                except:
                    pass
                
                # Extract skills
                skills_list = []
                try:
                    skills_container = card.find_element(By.CLASS_NAME, "tags-gt")
                    skill_elems = skills_container.find_elements(By.TAG_NAME, "li")
                    skills_list = [skill.text.strip() for skill in skill_elems if skill.text.strip()]
                except:
                    # Try alternative selector
                    try:
                        skill_elems = card.find_elements(By.CSS_SELECTOR, "ul.tags li")
                        skills_list = [skill.text.strip() for skill in skill_elems if skill.text.strip()]
                    except:
                        pass
                
                # Extract job description snippet
                description = "N/A"
                try:
                    desc_elem = card.find_element(By.CLASS_NAME, "job-desc")
                    description = desc_elem.text.strip()
                except:
                    pass
                
                # Extract company rating
                rating = "N/A"
                try:
                    rating_elem = card.find_element(By.CLASS_NAME, "comp-rating")
                    rating = rating_elem.text.strip()
                except:
                    pass
                
                # Extract posted date
                posted_date = "N/A"
                try:
                    date_elem = card.find_element(By.CLASS_NAME, "fleft")
                    posted_date = date_elem.text.strip()
                except:
                    pass

                # Create job data dictionary (matching opportunities table schema)
                job_data = {
                    "company_name": company,
                    "role": role,
                    "opportunity_type": "Full-time",  # Naukri doesn't specify, default to Full-time
                    "application_start_date": None,
                    "application_end_date": None,
                    "skills": ", ".join(skills_list) if skills_list else "N/A",
                    "experience_required": experience,
                    "job_portal_name": "Naukri.com",
                    "application_link": link,
                    # Extra fields for display (not in DB)
                    "location": job_location,
                    "salary": salary,
                    "description": description,
                    "company_rating": rating,
                    "posted_date": posted_date,
                    "scraped_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                jobs.append(job_data)
                print(f"  ✓ [{idx}/{len(job_cards)}] {role} at {company}")
                
            except Exception as e:
                print(f"  ✗ [{idx}/{len(job_cards)}] Error parsing job: {str(e)[:50]}")
                continue

        # Random delay between pages to avoid rate limiting
        if page < num_pages:
            delay = random.uniform(5, 8)
            print(f"\n⏳ Waiting {delay:.1f} seconds before next page...")
            time.sleep(delay)

    driver.quit()
    
    print(f"\n{'='*80}")
    print(f"🎯 Scraping Complete!")
    print(f"   Total jobs scraped: {len(jobs)}")
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
            print(f"✅ Successfully saved to database!")
        except Exception as e:
            print(f"❌ Database save failed: {e}")
    
    return jobs


def save_to_json(jobs, filename="naukri_jobs.json"):
    """Save jobs to JSON file."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved {len(jobs)} jobs to {filename}")


def save_to_csv(jobs, filename="naukri_jobs.csv"):
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


def print_summary(jobs, num_display=5):
    """Print a formatted summary of scraped jobs."""
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
        print(f"   💰 Salary: {job.get('salary', 'N/A')}")
        print(f"   🎓 Experience: {job['experience_required']}")
        print(f"   🔧 Skills: {job['skills'][:80]}..." if len(job['skills']) > 80 else f"   🔧 Skills: {job['skills']}")
        
        if job.get('company_rating') != "N/A":
            print(f"   ⭐ Rating: {job.get('company_rating')}")
        
        if job.get('posted_date') != "N/A":
            print(f"   📅 Posted: {job.get('posted_date')}")
        
        print(f"   🔗 Link: {job['application_link']}")
        print()


if __name__ == "__main__":
    # Configuration
    KEYWORD = "data analyst"
    LOCATION = ""  # Leave empty for all India, or specify like "Bangalore", "Mumbai"
    NUM_PAGES = 1  # Recommended: 1-3 to avoid rate limiting
    SAVE_TO_DB = True  # Set to True to save to database
    SAVE_FILES = True  # Set to True to also save JSON/CSV files
    
    # Scrape jobs
    results = scrape_naukri(
        keyword=KEYWORD,
        location=LOCATION,
        num_pages=NUM_PAGES,
        save_to_db=SAVE_TO_DB
    )
    
    # Display summary
    print_summary(results, num_display=5)
    
    # Save to files (optional)
    if results and SAVE_FILES:
        save_to_json(results, "naukri_jobs.json")
        save_to_csv(results, "naukri_jobs.csv")
        print("\n✅ Files saved: naukri_jobs.json and naukri_jobs.csv")
    
    print("\n✅ Done! Check your PostgreSQL database in pgAdmin4.")