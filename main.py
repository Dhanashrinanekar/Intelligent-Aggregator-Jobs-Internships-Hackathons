import sys
from datetime import datetime, timedelta
from database.models import get_db_session, Opportunity
from backend.app.scrapers.naukri_scraper import scrape_naukri
from backend.app.scrapers.indeed_api import scrape_indeed_simple
from backend.app.utils.date_utils import resolve_dates_for_job
#from backend.app.scrapers.linkedin_scraper import scrape_linkedin_jobs
from utils.data_cleaner import clean_opportunity_data
from utils.deduplicator import remove_duplicates
from sqlalchemy.exc import IntegrityError

def fetch_all_opportunities(keywords=None):
    """
    Fetch opportunities from all sources
    """
    if keywords is None:
        keywords = ["python developer", "data scientist", "software engineer"]
    
    all_opportunities = []
    
    print("\n" + "="*60)
    print("🚀 Starting Job & Hackathon Aggregator")
    print("="*60 + "\n")
    
    # Fetch from Naukri
    try:
        for keyword in keywords:
            print(f"\n📍 Fetching from Naukri for: {keyword}")
            naukri_jobs = scrape_naukri(keyword, num_pages=2, save_to_db=False)
            all_opportunities.extend(naukri_jobs)
    except Exception as e:
        print(f"❌ Naukri scraping failed: {e}")
    
    # Fetch from Indeed
    try:
        for keyword in keywords:
            print(f"\n📍 Fetching from Indeed for: {keyword}")
            indeed_jobs = scrape_indeed_simple(keyword)
            all_opportunities.extend(indeed_jobs)
    except Exception as e:
        print(f"❌ Indeed scraping failed: {e}")
    
    # Fetch from LinkedIn (commented out by default - enable if needed)
    # WARNING: LinkedIn may block your account for scraping
    # try:
    #     for keyword in keywords:
    #         print(f"\n📍 Fetching from LinkedIn for: {keyword}")
    #         linkedin_jobs = scrape_linkedin_jobs(keyword, num_jobs=5)
    #         all_opportunities.extend(linkedin_jobs)
    # except Exception as e:
    #     print(f"❌ LinkedIn scraping failed: {e}")
    
    print(f"\n\n📊 Total opportunities fetched: {len(all_opportunities)}")
    
    return all_opportunities


def process_and_store_opportunities(opportunities):
    """
    Clean, deduplicate, and store opportunities in database
    """
    print("\n" + "="*60)
    print("🔧 Processing Data")
    print("="*60 + "\n")
    
    # Clean data
    cleaned_opportunities = clean_opportunity_data(opportunities)
    
    # Remove duplicates
    unique_opportunities = remove_duplicates(cleaned_opportunities)
    
    # Store in database
    print("\n💾 Storing in database...")
    session = get_db_session()
    
    new_count = 0
    updated_count = 0
    skipped_count = 0
    
    for opp in unique_opportunities:
        # Resolve dates to ensure no NULL values
        resolve_dates_for_job(opp)
        # Safety net: if still None, set defaults
        if opp.get('application_start_date') is None:
            opp['application_start_date'] = datetime.utcnow()
        if opp.get('application_end_date') is None:
            opp['application_end_date'] = datetime.utcnow() + timedelta(days=20)
        
        try:
            # Check if opportunity already exists
            existing = session.query(Opportunity).filter_by(
                application_link=opp['application_link']
            ).first()
            
            if existing:
                # Update existing record
                for key, value in opp.items():
                    setattr(existing, key, value)
                existing.updated_at = datetime.utcnow()
                updated_count += 1
            else:
                # Create new record
                new_opportunity = Opportunity(**opp)
                session.add(new_opportunity)
                new_count += 1
        except IntegrityError as e:
            session.rollback()
            skipped_count += 1
            print(f"⚠️  Duplicate detected, skipping...")
            continue
        except Exception as e:
            session.rollback()
            print(f"❌ Error storing opportunity: {e}")
            continue
    
    # Commit all changes
    try:
        session.commit()
        print(f"\n✅ Database updated successfully!")
        print(f"   📝 New opportunities: {new_count}")
        print(f"   🔄 Updated opportunities: {updated_count}")
        print(f"   ⏭️  Skipped duplicates: {skipped_count}")
    except Exception as e:
        session.rollback()
        print(f"❌ Error committing to database: {e}")
    finally:
        session.close()
    
    return new_count, updated_count


def cleanup_expired_opportunities():
    """Delete expired opportunities from the database before adding new data."""
    session = get_db_session()
    try:
        now = datetime.utcnow()
        deleted = session.query(Opportunity).filter(
            Opportunity.application_end_date < now
        ).delete(synchronize_session=False)
        session.commit()
        if deleted:
            print(f"✅ Deleted {deleted} expired job(s) from database")
        return deleted
    except Exception as e:
        session.rollback()
        print(f"❌ Error cleaning up expired jobs: {e}")
        return 0
    finally:
        session.close()


def display_summary():
    """
    Display summary of stored opportunities
    """
    print("\n" + "="*60)
    print("📊 Database Summary")
    print("="*60 + "\n")
    
    session = get_db_session()
    
    try:
        total_count = session.query(Opportunity).count()
        print(f"Total opportunities in database: {total_count}")
        
        # Count by portal
        portals = session.query(
            Opportunity.job_portal_name, 
            session.query(Opportunity).filter_by(job_portal_name=Opportunity.job_portal_name).count()
        ).group_by(Opportunity.job_portal_name).all()
        
        print("\n📍 By Portal:")
        for portal, count in portals:
            print(f"   {portal}: {count}")
        
        # Count by type
        types = session.query(
            Opportunity.opportunity_type,
            session.query(Opportunity).filter_by(opportunity_type=Opportunity.opportunity_type).count()
        ).group_by(Opportunity.opportunity_type).all()
        
        print("\n🏷️  By Type:")
        for opp_type, count in types:
            print(f"   {opp_type}: {count}")
        
        # Latest 5 opportunities
        print("\n🆕 Latest 5 Opportunities:")
        latest = session.query(Opportunity).order_by(
            Opportunity.created_at.desc()
        ).limit(5).all()
        
        for i, opp in enumerate(latest, 1):
            print(f"\n   {i}. {opp.role} at {opp.company_name}")
            print(f"      Portal: {opp.job_portal_name}")
            print(f"      Link: {opp.application_link[:60]}...")
            
    except Exception as e:
        print(f"❌ Error fetching summary: {e}")
    finally:
        session.close()


def main():
    """
    Main execution function
    """
    try:
        # Define keywords to search
        keywords = [
            "python developer",
            "data scientist",
            "software engineer",
            "machine learning engineer"
        ]
        
        # Step 0: Remove expired job records first
        cleanup_expired_opportunities()

        # Step 1: Fetch opportunities
        opportunities = fetch_all_opportunities(keywords)
        
        if not opportunities:
            print("\n⚠️  No opportunities fetched. Exiting...")
            return
        
        # Step 2: Process and store
        new_count, updated_count = process_and_store_opportunities(opportunities)
        
        # Step 3: Display summary
        display_summary()
        
        print("\n" + "="*60)
        print("✅ Job Aggregator completed successfully!")
        print("="*60 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Process interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()