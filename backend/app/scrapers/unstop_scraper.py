from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import time
import random
import json
from datetime import datetime
import sys
import os

# Import database module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# try:
#     from database import JobDatabase
# except ImportError:
#     from database.db_operations import JobDatabase  # Import only when needed


def scrape_unstop(keyword="python", category="jobs", num_pages=1, save_to_db=True):
    """
    Scrape Unstop (formerly Dare2Compete) for opportunities.
    
    Args:
        keyword (str): Search keyword
        category (str): 'jobs', 'internships', 'competitions', or 'all'
        num_pages (int): Number of scroll/pages (recommended: 1-3)
        save_to_db (bool): Whether to save to database
    
    Returns:
        list: List of opportunity dictionaries
    """
    print(f"🔍 Scraping Unstop.com for '{keyword}' ({category})...")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Configure Chrome options - more aggressive for JavaScript sites
    chrome_options = Options()
    # Comment out headless for debugging
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--enable-javascript")

    # Initialize driver
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), 
        options=chrome_options
    )
    
    # Maximize window for better rendering
    driver.maximize_window()
    
    # Hide webdriver property
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })

    opportunities = []

    # Build URL based on category
    base_url = "https://unstop.com"
    if category == "jobs":
        url = f"{base_url}/jobs"
    elif category == "internships":
        url = f"{base_url}/internships"
    elif category == "competitions":
        url = f"{base_url}/competitions"
    elif category == "hackathons":
        url = f"{base_url}/hackathons"
    else:
        url = f"{base_url}/opportunities"
    
    # Add search parameter if keyword provided
    if keyword:
        url += f"?search={keyword.replace(' ', '%20')}"
    
    print(f"\n🌐 Loading Unstop page...")
    print(f"   URL: {url}")
    
    try:
        driver.get(url)
        print("   ⏳ Waiting for page to load...")
        time.sleep(8)  # Give more time for initial load
        
        # Scroll to trigger lazy loading
        print("   📜 Scrolling to load content...")
        for i in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
        
        # Try multiple selectors for cards
        selectors = [
            "div[class*='opportunityCard']",
            "div.card",
            "div[class*='card']",
            "article",
            "div[class*='listing']",
            "a[href*='/p/']",  # Unstop uses /p/ in URLs
        ]
        
        cards = []
        for selector in selectors:
            try:
                cards = driver.find_elements(By.CSS_SELECTOR, selector)
                if cards:
                    print(f"   ✅ Found {len(cards)} elements using selector: {selector}")
                    break
            except:
                continue
        
        if not cards:
            print("   ⚠️ No cards found with any selector. Trying links...")
            # Last resort - find all links
            all_links = driver.find_elements(By.TAG_NAME, "a")
            cards = [link for link in all_links if '/p/' in link.get_attribute('href') or '']
        
        if not cards:
            print("   ❌ Could not find any opportunity cards")
            # Save HTML for debugging
            with open("debug_unstop_full.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("   📄 Saved full page source to debug_unstop_full.html")
            
            # Print page structure for debugging
            print("\n   🔍 Page structure analysis:")
            try:
                body = driver.find_element(By.TAG_NAME, "body")
                print(f"   Body classes: {body.get_attribute('class')}")
                
                # Find main content area
                main_areas = driver.find_elements(By.CSS_SELECTOR, "main, div[id*='main'], div[class*='content']")
                for area in main_areas[:3]:
                    print(f"   Main area found: {area.tag_name} - {area.get_attribute('class')}")
            except:
                pass
            
            driver.quit()
            return []
        
        print(f"\n✅ Found {len(cards)} opportunity cards/links")
        
        # Process each card
        for idx, card in enumerate(cards[:50], 1):  # Limit to 50 to avoid too many
            try:
                # Get the link first
                try:
                    if card.tag_name == 'a':
                        link = card.get_attribute('href')
                    else:
                        link_elem = card.find_element(By.TAG_NAME, "a")
                        link = link_elem.get_attribute('href')
                    
                    if not link or '/p/' not in link:
                        continue
                        
                except:
                    continue
                
                # Extract text content
                text_content = card.text
                
                if not text_content or len(text_content) < 5:
                    continue
                
                # Split content into lines
                lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                
                if not lines:
                    continue
                
                # First line is usually the role/title
                role = lines[0] if lines else "N/A"
                
                # Try to find company name (usually second line)
                company = lines[1] if len(lines) > 1 else "Unstop"
                
                # Try to extract other details
                location = "N/A"
                deadline = "N/A"
                stipend = "N/A"
                opp_type = category.capitalize()
                
                for line in lines:
                    line_lower = line.lower()
                    if 'deadline' in line_lower or 'ends' in line_lower:
                        deadline = line
                    elif 'location' in line_lower or any(city in line_lower for city in ['bangalore', 'mumbai', 'delhi', 'remote']):
                        location = line
                    elif '₹' in line or 'stipend' in line_lower or 'salary' in line_lower:
                        stipend = line
                    elif any(t in line_lower for t in ['internship', 'job', 'competition', 'hackathon']):
                        opp_type = line

                # Create opportunity data
                opportunity_data = {
                    "company_name": company[:255] if company != "N/A" else "Unstop",
                    "role": role[:500],
                    "opportunity_type": opp_type[:100],
                    "application_start_date": None,
                    "application_end_date": None,
                    "skills": "N/A",
                    "experience_required": "N/A",
                    "job_portal_name": "Unstop.com",
                    "application_link": link,
                    # Extra fields
                    "location": location,
                    "stipend": stipend,
                    "deadline_str": deadline,
                    "scraped_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                opportunities.append(opportunity_data)
                print(f"  ✓ [{idx}] {role[:60]}... - {company[:30]}")
                
            except Exception as e:
                print(f"  ✗ [{idx}] Error: {str(e)[:50]}")
                continue

    except Exception as e:
        print(f"❌ Error loading page: {str(e)}")
        with open("debug_unstop_error.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
    
    finally:
        driver.quit()
    
    print(f"\n{'='*80}")
    print(f"🎯 Scraping Complete!")
    print(f"   Total opportunities scraped: {len(opportunities)}")
    print(f"   Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
    
    # Save to database if requested
    if save_to_db and opportunities:
        print("💾 Saving to database...")
        try:
            try:
                from database import JobDatabase
            except ImportError:
                from database.db_operations import JobDatabase
            db = JobDatabase()
            inserted = db.insert_jobs_bulk(opportunities)
            db.close()
            print(f"✅ Successfully saved to database!")
        except Exception as e:
            print(f"❌ Database save failed: {e}")
    
    return opportunities


def save_to_json(opportunities, filename="unstop_opportunities.json"):
    """Save opportunities to JSON file."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(opportunities, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved {len(opportunities)} opportunities to {filename}")


def print_summary(opportunities, num_display=5):
    """Print a formatted summary of scraped opportunities."""
    if not opportunities:
        print("⚠️ No opportunities to display")
        return
    
    print(f"\n{'='*80}")
    print(f"📋 OPPORTUNITIES SUMMARY (Showing {min(num_display, len(opportunities))} of {len(opportunities)})")
    print(f"{'='*80}\n")
    
    for i, opp in enumerate(opportunities[:num_display], 1):
        print(f"{i}. {opp['role']}")
        print(f"   🏢 Company: {opp['company_name']}")
        print(f"   📝 Type: {opp['opportunity_type']}")
        print(f"   📍 Location: {opp.get('location', 'N/A')}")
        print(f"   💰 Stipend: {opp.get('stipend', 'N/A')}")
        print(f"   📅 Deadline: {opp.get('deadline_str', 'N/A')}")
        print(f"   🔗 Link: {opp['application_link']}")
        print()


if __name__ == "__main__":
    # Configuration
    KEYWORD = "java"  # Search keyword (or leave empty for all)
    CATEGORY = "jobs"  # Options: 'jobs', 'internships', 'competitions', 'hackathons', 'all'
    SAVE_TO_DB = True
    SAVE_FILES = True
    
    print("🚀 Unstop.com Scraper")
    print("="*80)
    print(f"Searching for: {KEYWORD if KEYWORD else 'All opportunities'}")
    print(f"Category: {CATEGORY}")
    print("="*80 + "\n")
    
    # Scrape opportunities
    results = scrape_unstop(
        keyword=KEYWORD,
        category=CATEGORY,
        num_pages=1,
        save_to_db=SAVE_TO_DB
    )
    
    # Display summary
    print_summary(results, num_display=10)
    
    # Save to files
    if results and SAVE_FILES:
        save_to_json(results, f"unstop_{CATEGORY}.json")
        print(f"\n✅ File saved: unstop_{CATEGORY}.json")
    
    print("\n✅ Done! Check your PostgreSQL database in pgAdmin4.")