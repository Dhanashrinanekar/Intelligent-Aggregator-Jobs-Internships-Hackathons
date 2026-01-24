"""
Daily All Jobs Scraper - Uses ALL existing scrapers
Scrapes ALL new jobs from Indeed, Naukri, and Jooble (not keyword-specific)
Stores everything in database for frontend search
"""

import sys
import os
import time
from datetime import datetime
import json
import random

# Add paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scrapers'))

# Import all scrapers
from scrapers.indeed_scraper import scrape_indeed
from scrapers.naukri_scraper import scrape_naukri
from scrapers.jooble_api import JoobleJobAggregator

# Import database
from database.db_operations import JobDatabase

# Load environment
from dotenv import load_dotenv
load_dotenv()


# Broad categories to cover ALL types of jobs
JOB_CATEGORIES = [
    "software developer", "python developer", "java developer", "javascript developer",
    "web developer", "frontend developer", "backend developer", "full stack developer",
    "mobile developer", "android developer", "ios developer", "react developer",
    "nodejs developer", "php developer", "dotnet developer",
    "data scientist", "data analyst", "data engineer", "machine learning engineer",
    "artificial intelligence", "deep learning", "business intelligence", "data visualization",
    "devops engineer", "cloud engineer", "aws developer", "azure developer",
    "site reliability engineer", "kubernetes",
    "qa engineer", "test engineer", "automation tester", "manual tester",
    "ui ux designer", "graphic designer", "web designer", "product designer",
    "motion graphics",
    "product manager", "project manager", "business analyst", "scrum master",
    "program manager", "technical lead", "team lead", "operations manager",
    "account manager", "relationship manager",
    "sales executive", "business development", "marketing manager", "digital marketing",
    "content writer", "seo specialist", "social media manager", "sales manager",
    "accountant", "financial analyst", "finance manager", "chartered accountant",
    "tax consultant",
    "hr manager", "hr recruiter", "talent acquisition", "hr generalist",
    "consultant", "analyst", "engineer", "intern", "fresher"
]


def print_header(title):
    """Print formatted header."""
    print("\n" + "="*90)
    print(f"  {title}")
    print("="*90 + "\n")


def scrape_all_jobs_daily(config):
    """Scrape ALL new jobs from multiple portals across various categories."""
    print_header("DAILY ALL JOBS AGGREGATOR - COMPREHENSIVE SCRAPING")
    
    start_time = datetime.now()
    print(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total categories: {len(config['categories'])}")
    print(f"Portals: {', '.join(config['portals'])}")
    print(f"Pages per category per portal: {config['pages_per_category']}")
    
    all_jobs = []
    stats = {
        'total_jobs': 0,
        'by_portal': {},
        'by_category': {},
        'duplicates_skipped': 0,
        'errors': []
    }
    
    seen_links = set()
    
    jooble_api = None
    if 'jooble' in config['portals']:
        jooble_key = os.getenv("JOOBLE_API_KEY")
        if jooble_key:
            jooble_api = JoobleJobAggregator(jooble_key)
            print("Jooble API initialized")
        else:
            print("Jooble API key not found, skipping Jooble")
            config['portals'].remove('jooble')
    
    for cat_idx, category in enumerate(config['categories'], 1):
        print_header(f"CATEGORY {cat_idx}/{len(config['categories'])}: {category.upper()}")
        
        category_jobs = []
        category_stats = {'indeed': 0, 'naukri': 0, 'jooble': 0}
        
        # Indeed
        if 'indeed' in config['portals']:
            print(f"Indeed: Scraping '{category}'...")
            try:
                indeed_jobs = scrape_indeed(
                    keyword=category,
                    location=config.get('location', 'India'),
                    num_pages=config['pages_per_category'],
                    save_to_db=False
                )
                new_jobs = [j for j in indeed_jobs if j['application_link'] not in seen_links]
                for j in new_jobs:
                    seen_links.add(j['application_link'])
                
                category_jobs.extend(new_jobs)
                category_stats['indeed'] = len(new_jobs)
                stats['duplicates_skipped'] += len(indeed_jobs) - len(new_jobs)
                print(f"   Indeed: {len(new_jobs)} new | {len(indeed_jobs)-len(new_jobs)} duplicates")
                time.sleep(random.uniform(2, 4))
                
            except Exception as e:
                error_msg = f"Indeed failed for '{category}': {str(e)[:50]}"
                print(f"   {error_msg}")
                stats['errors'].append(error_msg)
        
        # Naukri
        if 'naukri' in config['portals']:
            print(f"Naukri: Scraping '{category}'...")
            try:
                naukri_jobs = scrape_naukri(
                    keyword=category,
                    location="",
                    num_pages=config['pages_per_category'],
                    save_to_db=False
                )
                new_jobs = [j for j in naukri_jobs if j['application_link'] not in seen_links]
                for j in new_jobs:
                    seen_links.add(j['application_link'])
                
                category_jobs.extend(new_jobs)
                category_stats['naukri'] = len(new_jobs)
                stats['duplicates_skipped'] += len(naukri_jobs) - len(new_jobs)
                print(f"   Naukri: {len(new_jobs)} new | {len(naukri_jobs)-len(new_jobs)} duplicates")
                time.sleep(random.uniform(2, 4))
                
            except Exception as e:
                error_msg = f"Naukri failed for '{category}': {str(e)[:50]}"
                print(f"   {error_msg}")
                stats['errors'].append(error_msg)
        
        # Jooble
        if 'jooble' in config['portals'] and jooble_api:
            print(f"Jooble: Fetching '{category}'...")
            try:
                jooble_jobs = jooble_api.search_jobs(
                    keyword=category,
                    location=config.get('location', 'India'),
                    num_pages=config['pages_per_category'],
                    save_to_db=False
                )
                new_jobs = [j for j in jooble_jobs if j['application_link'] not in seen_links]
                for j in new_jobs:
                    seen_links.add(j['application_link'])
                
                category_jobs.extend(new_jobs)
                category_stats['jooble'] = len(new_jobs)
                stats['duplicates_skipped'] += len(jooble_jobs) - len(new_jobs)
                print(f"   Jooble: {len(new_jobs)} new | {len(jooble_jobs)-len(new_jobs)} duplicates")
                time.sleep(random.uniform(1, 2))
                
            except Exception as e:
                error_msg = f"Jooble failed for '{category}': {str(e)[:50]}"
                print(f"   {error_msg}")
                stats['errors'].append(error_msg)
        
        stats['by_category'][category] = len(category_jobs)
        all_jobs.extend(category_jobs)
        
        print(f"\nCategory '{category}' complete: {len(category_jobs)} jobs")
        print(f"   Indeed: {category_stats['indeed']} | Naukri: {category_stats['naukri']} | Jooble: {category_stats['jooble']}")
        
        if cat_idx % 10 == 0 and all_jobs:
            print(f"\nIntermediate save: {len(all_jobs)} jobs so far...")
            try:
                db = JobDatabase()
                db.insert_jobs_bulk(all_jobs[-len(category_jobs):])
                db.close()
            except Exception as e:
                print(f"   Intermediate save failed: {e}")
        
        if cat_idx < len(config['categories']):
            delay = config.get('delay_between_categories', 8)
            print(f"Waiting {delay}s before next category...\n")
            time.sleep(delay)
    
    for job in all_jobs:
        portal = job['job_portal_name']
        stats['by_portal'][portal] = stats['by_portal'].get(portal, 0) + 1
    
    stats['total_jobs'] = len(all_jobs)
    
    if config['save_to_db'] and all_jobs:
        print_header("FINAL DATABASE SAVE")
        try:
            db = JobDatabase()
            inserted = db.insert_jobs_bulk(all_jobs)
            db_stats = db.get_statistics()
            db.close()
            print("Database save completed!")
            print(f"\nUpdated Database Statistics:")
            print(f"   Total Jobs in DB: {db_stats.get('total_jobs', 0):,}")
            print(f"   Total Companies: {db_stats.get('total_companies', 0):,}")
            print(f"   Jobs Added Today: {db_stats.get('jobs_scraped_today', 0):,}")
        except Exception as e:
            print(f"Database save failed: {e}")
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print_header("DAILY SCRAPING COMPLETE")
    print(f"Total Duration: {duration/60:.1f} minutes ({duration:.0f} seconds)")
    
    print(f"\nJobs Scraped by Portal:")
    for portal, count in stats['by_portal'].items():
        print(f"   {portal:20} {count:,} jobs")
    
    print(f"\nTop 15 Categories by Job Count:")
    top_categories = sorted(stats['by_category'].items(), key=lambda x: x[1], reverse=True)[:15]
    for category, count in top_categories:
        print(f"   {category:30} {count:4} jobs")
    
    print(f"\nSummary:")
    print(f"   Total Unique Jobs: {stats['total_jobs']:,}")
    print(f"   Duplicates Skipped: {stats['duplicates_skipped']:,}")
    print(f"   Categories Scraped: {len(config['categories'])}")
    print(f"   Errors Encountered: {len(stats['errors'])}")
    
    if stats['errors']:
        print(f"\nErrors (first 5):")
        for error in stats['errors'][:5]:
            print(f"   • {error}")
    
    print(f"\nFinished at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    log_data = {
        'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
        'end_time': end_time.strftime('%Y-%m-%d %H:%M:%S'),
        'duration_seconds': duration,
        'stats': stats,
        'config': {k: v for k, v in config.items() if k != 'categories'}
    }
    
    log_filename = f"scraping_log_{start_time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_filename, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)
    
    print(f"Session log: {log_filename}")
    print("="*90 + "\n")
    
    return all_jobs, stats


def get_default_config():
    return {
        'categories': JOB_CATEGORIES,
        'portals': ['indeed', 'naukri', 'jooble'],
        'location': 'India',
        'pages_per_category': 1,
        'save_to_db': True,
        'delay_between_categories': 8,
    }


def get_quick_config():
    return {
        'categories': [
            "software developer",
            "data scientist",
            "business analyst",
            "sales executive",
            "accountant"
        ],
        'portals': ['indeed', 'naukri', 'jooble'],
        'location': 'India',
        'pages_per_category': 1,
        'save_to_db': True,
        'delay_between_categories': 5,
    }


def get_tech_only_config():
    return {
        'categories': [
            "software developer", "python developer", "java developer", "javascript developer",
            "web developer", "frontend developer", "backend developer", "full stack developer",
            "mobile developer", "android developer", "ios developer", "react developer",
            "data scientist", "data analyst", "machine learning engineer", "devops engineer",
            "cloud engineer", "qa engineer", "ui ux designer", "product manager",
            "business analyst", "project manager", "technical lead"
        ],
        'portals': ['indeed', 'naukri', 'jooble'],
        'location': 'India',
        'pages_per_category': 1,
        'save_to_db': True,
        'delay_between_categories': 6,
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Daily All Jobs Aggregator - Scrape broadly from all portals'
    )
    parser.add_argument('--mode', choices=['full', 'quick', 'tech'], default='quick',
                        help='Scraping mode: full (all 70+ categories), quick (5 categories), tech (23 tech categories)')
    parser.add_argument('--pages', type=int, default=1,
                        help='Pages per category (default: 1)')
    parser.add_argument('--portals', nargs='+', 
                        choices=['indeed', 'naukri', 'jooble'],
                        help='Specific portals to use')
    
    args = parser.parse_args()
    
    if args.mode == 'full':
        print("FULL MODE: Scraping ALL 70+ job categories\n")
        config = get_default_config()
    elif args.mode == 'tech':
        print("TECH MODE: Scraping 23 tech job categories\n")
        config = get_tech_only_config()
    else:
        print("QUICK MODE: Scraping 5 main categories (for testing)\n")
        config = get_quick_config()
    
    if args.pages:
        config['pages_per_category'] = args.pages
    if args.portals:
        config['portals'] = args.portals
    
    if args.mode == 'full':
        print(f"FULL MODE will scrape {len(config['categories'])} categories!")
        print(f"Estimated time: 2-3 hours")
        print(f"Expected jobs: 1000-2000+")
        confirm = input("\nContinue? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled")
            sys.exit(0)
    
    try:
        jobs, stats = scrape_all_jobs_daily(config)
        print("\nDaily scraping completed!")
        print(f"{stats['total_jobs']:,} jobs saved to database")
        print("Users can now search these jobs on frontend")
        print("\nFrontend query examples:")
        print("   SELECT * FROM opportunities WHERE role ILIKE '%python%';")
        print("   SELECT * FROM opportunities WHERE skills ILIKE '%react%';")
        print("   SELECT * FROM opportunities WHERE company_name ILIKE '%google%';")
    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
