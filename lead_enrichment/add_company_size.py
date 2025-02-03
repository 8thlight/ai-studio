import pandas as pd
import os
import requests
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Cache to store company size results
_company_size_cache = {}

def get_company_size(company_name: str, industry: str) -> str:
    """
    Query Perplexity API to determine company size based on name and industry.
    Returns the number of employees as a range (e.g., "100-150") or single number (e.g., "5000")
    If unable to determine, returns "UNKNOWN"
    Uses an in-memory cache to avoid duplicate API calls.
    """
    # Create cache key from company name and industry
    cache_key = (company_name.lower().strip(), industry.lower().strip())
    
    # Check cache first
    if cache_key in _company_size_cache:
        cached_result = _company_size_cache[cache_key]
        print(f"Cache hit for: {company_name} ({industry}) -> {cached_result}")
        return cached_result

    print(f"Cache miss for: {company_name} ({industry})")
    
    api_key = os.getenv('PERPLEXITY_API_KEY')
    if not api_key:
        raise ValueError("PERPLEXITY_API_KEY environment variable is required")

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    prompt = f'''Find the current or most recent employee count for {company_name}. They are in the {industry} industry. Only respond with:
    - An exact number if you have recent factual data (e.g., '5000')
    - A specific range if you have approximate data (e.g., '100-150')
    - 'UNKNOWN' if you cannot find reliable data
    Respond ONLY with the number, range, or UNKNOWN - no other text.'''
    
    print(f"\nQuerying for: {company_name} ({industry})")
    print(f"Prompt: {prompt}")
    
    try:
        response = requests.post(
            'https://api.perplexity.ai/chat/completions',
            headers=headers,
            json={
                'model': 'sonar',
                'messages': [{'role': 'user', 'content': prompt}]
            }
        )
        
        if response.status_code == 200:
            size = response.json()['choices'][0]['message']['content'].strip()
            print(f"Response: {size}")
            # Clean up the response - remove any non-numeric characters except hyphen and verify format
            size = size.replace(',', '').replace(' ', '')
            if size == 'UNKNOWN':
                _company_size_cache[cache_key] = size
                return size
            
            # Check if it's a valid range (e.g., 100-150) or single number
            if '-' in size:
                start, end = size.split('-')
                if start.isdigit() and end.isdigit():
                    return size
            elif size.isdigit():
                _company_size_cache[cache_key] = size
                return size
            
            _company_size_cache[cache_key] = 'UNKNOWN'
            return 'UNKNOWN'
        else:
            print(f"Error with API call for {company_name}: {response.status_code}")
            return 'UNKNOWN'
            
    except Exception as e:
        print(f"Exception when processing {company_name}: {str(e)}")
        return 'UNKNOWN'
    
    # Add a small delay to avoid hitting rate limits
    time.sleep(0.5)

def main():
    # Read the Excel file from the data directory
    excel_path = "data/hubspot-crm-exports-ai-nurture-test-updated.xlsx"
    df = pd.read_excel(excel_path, sheet_name="Original Data")
    
    # Debug: Print column names
    print("\nAvailable columns in Excel:")
    for col in df.columns:
        print(f"  - {col}")
    
    # Get the correct column names
    company_col = "Company name"
    industry_col = "Cleaned Industry"
    
    if company_col not in df.columns or industry_col not in df.columns:
        raise ValueError(f"Could not find required columns. Need '{company_col}' and '{industry_col}' columns.")
    
    print(f"\nUsing columns:\n  Company: {company_col}\n  Industry: {industry_col}")
    
    # Add Size column if it doesn't exist
    if "Size" not in df.columns:
        print("Adding Size column...")
        df["Size"] = ""
    
    # Process each company and save after each one
    total_companies = len(df)
    processed_count = 0
    skipped_count = 0
    
    for idx, row in df.iterrows():
        # Skip if we already have data for this company
        current_size = str(row.get("Size", "")).strip()
        if current_size and current_size.upper() != "NAN":
            print(f"\nSkipping company {idx + 1}/{total_companies} - already has size: {current_size}")
            skipped_count += 1
            continue
            
        print(f"\nProcessing company {idx + 1}/{total_companies}")
        df.at[idx, "Size"] = get_company_size(row[company_col], row[industry_col])
        processed_count += 1
        
        # Save after each company
        df.to_excel(excel_path, sheet_name="Original Data", index=False)
        print(f"Saved progress after company {idx + 1}")
    
    print(f"\nCompleted: {processed_count} processed, {skipped_count} skipped (already had data)")
    
    print(f"Processed {len(df)} companies")
    print("\nFirst few rows with Size:")
    print(df[["Company Name", "Cleaned Industry", "Size"]].head())

if __name__ == "__main__":
    main()
