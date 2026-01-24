import pandas as pd
from difflib import SequenceMatcher

def similar(a, b):
    """Calculate similarity between two strings"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def remove_duplicates(opportunities):
    """
    Remove duplicate opportunities based on:
    - Exact URL match
    - Similar company + role combination
    
    Args:
        opportunities: List of opportunity dictionaries
    
    Returns:
        List of unique opportunities
    """
    print(f"🔍 Checking for duplicates in {len(opportunities)} opportunities...")
    
    if not opportunities:
        return []
    
    # Convert to DataFrame for easier manipulation
    df = pd.DataFrame(opportunities)
    
    # Remove exact URL duplicates
    initial_count = len(df)
    df = df.drop_duplicates(subset=['application_link'], keep='first')
    url_dupes = initial_count - len(df)
    
    # Remove similar opportunities (same company + similar role)
    unique_opportunities = []
    seen_combinations = []
    
    for _, row in df.iterrows():
        is_duplicate = False
        
        for seen in seen_combinations:
            # Check if company matches and role is very similar
            if (row['company_name'].lower() == seen['company'].lower() and
                similar(row['role'], seen['role']) > 0.85):  # 85% similarity threshold
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_opportunities.append(row.to_dict())
            seen_combinations.append({
                'company': row['company_name'],
                'role': row['role']
            })
    
    similarity_dupes = len(df) - len(unique_opportunities)
    
    print(f"✅ Removed {url_dupes} exact duplicates and {similarity_dupes} similar duplicates")
    print(f"📊 Final count: {len(unique_opportunities)} unique opportunities")
    
    return unique_opportunities


if __name__ == "__main__":
    # Test
    sample_data = [
        {'company_name': 'Google', 'role': 'Software Engineer', 'application_link': 'link1'},
        {'company_name': 'Google', 'role': 'Software Engineer', 'application_link': 'link1'},  # Exact duplicate
        {'company_name': 'Google', 'role': 'Sr. Software Engineer', 'application_link': 'link2'},  # Similar
        {'company_name': 'Amazon', 'role': 'SDE', 'application_link': 'link3'},
    ]
    
    unique = remove_duplicates(sample_data)
    print(f"\nUnique opportunities: {len(unique)}")