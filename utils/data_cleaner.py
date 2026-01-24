import re
from datetime import datetime
import pandas as pd

def clean_company_name(name):
    """Clean and normalize company names"""
    if not name or name == "N/A":
        return "Unknown"
    
    # Remove extra whitespace
    name = ' '.join(name.split())
    
    # Remove common suffixes for normalization
    name = re.sub(r'\s+(Pvt\.?|Ltd\.?|Inc\.?|LLC|Corporation|Corp\.?)$', '', name, flags=re.IGNORECASE)
    
    return name.strip().title()


def clean_role(role):
    """Clean role/title"""
    if not role or role == "N/A":
        return "Not Specified"
    
    # Remove extra whitespace
    role = ' '.join(role.split())
    
    return role.strip().title()


def clean_skills(skills):
    """Clean and normalize skills"""
    if not skills or skills == "N/A":
        return ""
    
    # If it's a string with commas
    if isinstance(skills, str):
        skills_list = [s.strip().lower() for s in skills.split(',')]
        # Remove duplicates and empty strings
        skills_list = list(set([s for s in skills_list if s]))
        return ', '.join(sorted(skills_list))
    
    return skills


def clean_experience(experience):
    """Normalize experience field"""
    if not experience or experience == "N/A":
        return "Not Specified"
    
    # Extract years if mentioned
    match = re.search(r'(\d+)\s*-?\s*(\d+)?\s*(year|yr)', experience, re.IGNORECASE)
    if match:
        return experience.strip()
    
    return experience.strip()


def parse_date(date_str):
    """Try to parse date from various formats"""
    if not date_str or date_str == "N/A":
        return None
    
    # Common date formats
    formats = [
        '%Y-%m-%d',
        '%d-%m-%Y',
        '%m/%d/%Y',
        '%d/%m/%Y',
        '%B %d, %Y',
        '%d %B %Y'
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return None


def clean_url(url):
    """Validate and clean URLs"""
    if not url or url == "N/A":
        return None
    
    # Ensure URL starts with http
    if not url.startswith('http'):
        url = 'https://' + url
    
    return url.strip()


def clean_opportunity_data(data_list):
    """
    Clean all opportunity data
    
    Args:
        data_list: List of dictionaries containing opportunity data
    
    Returns:
        List of cleaned dictionaries
    """
    print(f"🧹 Cleaning {len(data_list)} opportunities...")
    
    cleaned_data = []
    
    for data in data_list:
        try:
            cleaned = {
                'company_name': clean_company_name(data.get('company_name')),
                'role': clean_role(data.get('role')),
                'opportunity_type': data.get('opportunity_type', 'job').lower(),
                'application_start_date': parse_date(data.get('application_start_date')),
                'application_end_date': parse_date(data.get('application_end_date')),
                'skills': clean_skills(data.get('skills')),
                'experience_required': clean_experience(data.get('experience_required')),
                'job_portal_name': data.get('job_portal_name', 'Unknown'),
                'application_link': clean_url(data.get('application_link'))
            }
            
            # Skip if no valid application link
            if not cleaned['application_link']:
                continue
            
            cleaned_data.append(cleaned)
            
        except Exception as e:
            print(f"❌ Error cleaning record: {e}")
            continue
    
    print(f"✅ Cleaned {len(cleaned_data)} opportunities (removed {len(data_list) - len(cleaned_data)} invalid)")
    
    return cleaned_data


if __name__ == "__main__":
    # Test
    sample_data = [{
        'company_name': '  GOOGLE  INC.  ',
        'role': 'software ENGINEER',
        'skills': 'Python, python, Java, JAVA',
        'experience_required': '2-5 years',
        'application_link': 'google.com/jobs'
    }]
    
    cleaned = clean_opportunity_data(sample_data)
    print(cleaned)