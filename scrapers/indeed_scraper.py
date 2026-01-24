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
from database.db_operations import JobDatabase


def scrape_indeed(keyword="python developer", location="India", num_pages=1, save_to_db=True):
    """
    Scrape Indeed.com for job listings.
    
    Args:
        keyword (str): Job search keyword
        location (str): Job location
        num_pages (int): Number of pages to scrape (recommended: 1-2)
        save_to_db (bool): Whether to save to database
    
    Returns:
        list: List of job dictionaries
    """
    print(f"🔍 Scraping Indeed.com for '{keyword}' in '{location}'...")
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

    for page in range(num_pages):
        start = page * 10  # Indeed shows 10 jobs per page
        url = f"https://in.indeed.com/jobs?q={keyword.replace(' ', '+')}&l={location.replace(' ', '+')}&start={start}"
        
        print(f"\n🌐 Loading page {page + 1}...")
        print(f"   URL: {url}")
        
        try:
            driver.get(url)
            
            # Wait for job cards to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "job_seen_beacon"))
            )
            time.sleep(random.uniform(3, 5))
            
        except Exception as e:
            print(f"⚠️ Timeout on page {page + 1} - Indeed may be rate limiting")
            print(f"   Error: {str(e)[:100]}")
            break

        # Find all job cards
        job_cards = driver.find_elements(By.CSS_SELECTOR, "div.job_seen_beacon")
        
        if not job_cards:
            print(f"⚠️ No jobs found on page {page + 1}")
            break

        print(f"✅ Page {page + 1}: Found {len(job_cards)} jobs")

        for idx, card in enumerate(job_cards, 1):
            try:
                # Extract job title
                title_elem = card.find_element(By.CSS_SELECTOR, "h2.jobTitle span")
                role = title_elem.text.strip()
                
                # Extract company name
                company_elem = card.find_element(By.CSS_SELECTOR, "span[data-testid='company-name']")
                company = company_elem.text.strip()
                
                # Extract job link
                link_elem = card.find_element(By.CSS_SELECTOR, "h2.jobTitle a")
                job_id = link_elem.get_attribute("data-jk")
                link = f"https://in.indeed.com/viewjob?jk={job_id}" if job_id else link_elem.get_attribute("href")
                
                # Extract location
                job_location = "N/A"
                try:
                    location_elem = card.find_element(By.CSS_SELECTOR, "div[data-testid='text-location']")
                    job_location = location_elem.text.strip()
                except:
                    pass
                
                # Extract salary
                salary = "N/A"
                try:
                    salary_elem = card.find_element(By.CSS_SELECTOR, "div[data-testid='attribute_snippet_testid']")
                    salary_text = salary_elem.text.strip()
                    # Check if it's actually a salary (contains currency or numbers)
                    if any(char in salary_text for char in ['₹', '$', '€', '£']) or \
                       (any(char.isdigit() for char in salary_text) and 'lakh' in salary_text.lower()):
                        salary = salary_text
                except:
                    pass
                
                # Extract job description/snippet
                description = "N/A"
                skills_list = []
                try:
                    snippet_elems = card.find_elements(By.CSS_SELECTOR, "div.slider_container li")
                    if snippet_elems:
                        skills_list = [elem.text.strip() for elem in snippet_elems if elem.text.strip()]
                        description = " | ".join(skills_list)
                except:
                    pass
                
                # Extract job type (Full-time, Contract, etc.)
                job_type = "Full-time"  # Default
                try:
                    metadata_elems = card.find_elements(By.CSS_SELECTOR, "div.metadata.css-5zy3wz.eu4oa1w0 div")
                    for elem in metadata_elems:
                        text = elem.text.strip().lower()
                        if any(keyword in text for keyword in ['full-time', 'part-time', 'contract', 'temporary', 'internship', 'freelance']):
                            job_type = elem.text.strip()
                            break
                except:
                    pass
                
                # Extract company rating (if available)
                rating = "N/A"
                try:
                    rating_elem = card.find_element(By.CSS_SELECTOR, "span[data-testid='holistic-rating']")
                    rating = rating_elem.text.strip()
                except:
                    pass

                # Create job data dictionary (matching your opportunities table schema)
                job_data = {
                    "company_name": company,
                    "role": role,
                    "opportunity_type": job_type,
                    "application_start_date": None,  # Indeed doesn't provide this
                    "application_end_date": None,    # Indeed doesn't provide this
                    "skills": ", ".join(skills_list) if skills_list else "N/A",
                    "experience_required": "N/A",
                    "job_portal_name": "Indeed.com",
                    "application_link": link,
                    # Extra fields for display (not in DB)
                    "location": job_location,
                    "salary": salary,
                    "description": description,
                    "company_rating": rating,
                    "scraped_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                jobs.append(job_data)
                print(f"  ✓ [{idx}/{len(job_cards)}] {role} at {company}")
                
            except Exception as e:
                print(f"  ✗ [{idx}/{len(job_cards)}] Error parsing job: {str(e)[:50]}")
                continue

        # Random delay between pages to avoid rate limiting
        if page < num_pages - 1:
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
            db = JobDatabase()
            inserted = db.insert_jobs_bulk(jobs)
            db.close()
            print(f"✅ Successfully saved to database!")
        except Exception as e:
            print(f"❌ Database save failed: {e}")
    
    return jobs


def save_to_json(jobs, filename="indeed_jobs.json"):
    """Save jobs to JSON file."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved {len(jobs)} jobs to {filename}")


def save_to_csv(jobs, filename="indeed_jobs.csv"):
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
        print(f"   📍 Location: {job['location']}")
        print(f"   💰 Salary: {job['salary']}")
        print(f"   📝 Type: {job['opportunity_type']}")
        
        if job['company_rating'] != "N/A":
            print(f"   ⭐ Rating: {job['company_rating']}")
        
        desc = job['description']
        if len(desc) > 100:
            print(f"   📄 Description: {desc[:100]}...")
        else:
            print(f"   📄 Description: {desc}")
        
        print(f"   🔗 Link: {job['application_link']}")
        print()


if __name__ == "__main__":
    # Configuration
    KEYWORD = "python developer"
    LOCATION = "India"
    NUM_PAGES = 1  # Recommended: 1-2 to avoid rate limiting
    SAVE_TO_DB = True  # Set to True to save to database
    SAVE_FILES = True  # Set to True to also save JSON/CSV files
    
    # Scrape jobs
    results = scrape_indeed(
        keyword=KEYWORD,
        location=LOCATION,
        num_pages=NUM_PAGES,
        save_to_db=SAVE_TO_DB
    )
    
    # Display summary
    print_summary(results, num_display=5)
    
    # Save to files (optional)
    if results and SAVE_FILES:
        save_to_json(results, "indeed_jobs.json")
        save_to_csv(results, "indeed_jobs.csv")
        print("\n✅ Files saved: indeed_jobs.json and indeed_jobs.csv")
    
    print("\n✅ Done! Check your PostgreSQL database in pgAdmin4.")