#!/usr/bin/env python3
"""Test script to verify date resolution in scrapers"""

import sys
import os

# Add repo root to path
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from backend.app.scrapers.naukri_scraper import scrape_naukri

if __name__ == "__main__":
    print("Testing Naukri scraper with date resolution...")
    jobs = scrape_naukri('python developer', 'India', 1, save_to_db=False)

    print(f"Found {len(jobs)} jobs")

    if jobs:
        job = jobs[0]
        print(f"Sample job: {job['role']} at {job['company_name']}")
        print(f"Start date: {job['application_start_date']}")
        print(f"End date: {job['application_end_date']}")
        print(f"Both dates are not None: {job['application_start_date'] is not None and job['application_end_date'] is not None}")
    else:
        print("No jobs found")