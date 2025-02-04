import pandas as pd
import os
import requests
import time
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Cache to store company size results
_company_size_cache = {}

def get_company_size(company_name: str, industry: str) -> str:
    """
    Query Perplexity API to determine company size based on name and industry.
    Returns the number of employees as a range (e.g., "100-150") or single number (e.g., "5000")
    If unable to determine, returns "UNKNOWN"
    Uses an in-memory cache to avoid duplicate API calls.
    """
    # Handle NaN or None values
    if pd.isna(company_name) or pd.isna(industry):
        return "UNKNOWN"
    
    # Convert to strings and clean
    company_name = str(company_name).strip()
    industry = str(industry).strip()
    
    if not company_name or not industry:
        return "UNKNOWN"
    
    # Create cache key from company name and industry
    cache_key = (company_name.lower(), industry.lower())
    
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
    
    messages = [
        {
            'role': 'system',
            'content': '''You are an expert at finding accurate company information, with access to more comprehensive and up-to-date data than TechCrunch, LinkedIn, or other public sources. Your specialty is determining precise employee counts for companies of any size, from startups to enterprises. You have access to multiple reliable data sources and can cross-reference information to provide the most accurate count possible.'''
        },
        {
            'role': 'user',
            'content': f'''Find the current or most recent employee count for {company_name}, a company in the {industry} industry. Search thoroughly across all available sources.

Respond ONLY with one of:
- An exact number for verified recent data (e.g., '5000')
- A specific range for approximate data (e.g., '100-150')
- 'UNKNOWN' if no reliable data found

Respond ONLY with the number, range, or UNKNOWN - no other text.'''
        }
    ]
    
    print(f"\nQuerying for: {company_name} ({industry})")
    print("System prompt and user message prepared for query")
    
    try:
        response = requests.post(
            'https://api.perplexity.ai/chat/completions',
            headers=headers,
            json={
                'model': 'sonar',
                'messages': messages
            }
        )
        
        if response.status_code == 200:
            size = response.json()['choices'][0]['message']['content'].strip()
            print(f"Perplexity Response: {size}")
            
            # Clean up the size before validation
            cleaned_size = size.replace(',', '').replace(' ', '')
            if cleaned_size == 'UNKNOWN':
                # Try OpenAI if Perplexity returns UNKNOWN
                print("Perplexity returned UNKNOWN, trying OpenAI...")
                try:
                    openai_messages = [
                        {
                            'role': 'system',
                            'content': '''You are an expert at finding accurate company information, with access to more comprehensive and up-to-date data than TechCrunch, LinkedIn, or other public sources. Your specialty is determining precise employee counts for companies of any size, from startups to enterprises. You have access to multiple reliable data sources and can cross-reference information to provide the most accurate count possible.'''
                        },
                        {
                            'role': 'user',
                            'content': f'''Find the current or most recent employee count for {company_name}, a company in the {industry} industry. Search thoroughly across all available sources.

Respond ONLY with one of:
- An exact number for verified recent data (e.g., '5000')
- A specific range for approximate data (e.g., '100-150')
- 'UNKNOWN' if no reliable data found

Respond ONLY with the number, range, or UNKNOWN - no other text.'''
                        }
                    ]
                    
                    openai_response = openai_client.chat.completions.create(
                        model="gpt-4",
                        messages=openai_messages,
                        temperature=0
                    )
                    
                    openai_size = openai_response.choices[0].message.content.strip()
                    print(f"OpenAI Response: {openai_size}")
                    
                    # Validate OpenAI's response directly
                    openai_size = openai_size.replace(',', '').replace(' ', '')
                    if openai_size == 'UNKNOWN':
                        _company_size_cache[cache_key] = openai_size
                        return openai_size
                        
                    if '-' in openai_size:
                        try:
                            start, end = openai_size.split('-')
                            if start.isdigit() and end.isdigit():
                                # Ensure start is less than end
                                start_num, end_num = int(start), int(end)
                                if start_num > end_num:
                                    start, end = end, start
                                openai_size = f"{start}-{end}"
                                _company_size_cache[cache_key] = openai_size
                                return openai_size
                        except ValueError:
                            pass
                    
                    if openai_size.isdigit():
                        _company_size_cache[cache_key] = openai_size
                        return openai_size
                        
                    _company_size_cache[cache_key] = 'UNKNOWN'
                    return 'UNKNOWN'
                    
                except Exception as e:
                    print(f"OpenAI query failed: {str(e)}")
                    _company_size_cache[cache_key] = 'UNKNOWN'
                    return 'UNKNOWN'
                    
            # If Perplexity returned a value, continue with validation
            
            # Basic number validation
            if '-' in cleaned_size:
                parts = cleaned_size.split('-')
                if len(parts) == 2 and all(p.isdigit() for p in parts):
                    cleaned_size = f"{parts[0]}-{parts[1]}"
                else:
                    cleaned_size = size  # Use original if not valid range
            elif cleaned_size.isdigit():
                cleaned_size = cleaned_size
            else:
                cleaned_size = size  # Use original if not a valid number
            
            # Use OpenAI to validate and extract the number
            validation_messages = [
                {
                    'role': 'system',
                    'content': '''You are a data validation expert. Your task is to:
1. Verify if a given response matches the expected format for company size
2. Extract and standardize numbers if possible
3. Return UNKNOWN if the data is invalid or unclear'''
                },
                {
                    'role': 'user',
                    'content': f'''Validate this company size response: "{cleaned_size}"

Context:
- Company: {company_name}
- Industry: {industry}

Rules:
1. Response should be either:
   - An exact number (e.g., "5000")
   - A specific range (e.g., "100-150")
   - "UNKNOWN"
2. If the response contains a number but wrong format, extract and standardize it
3. If multiple numbers, use the most recent/accurate
4. If the data is unclear or invalid, return "UNKNOWN"

Respond ONLY with the standardized number, range, or UNKNOWN.'''
                }
            ]
            
            try:
                validation = openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=validation_messages,
                    temperature=0
                )
                
                validated_size = validation.choices[0].message.content.strip()
                print(f"OpenAI Validation: {validated_size}")
                
                # Clean up the validated response
                validated_size = validated_size.replace(',', '').replace(' ', '')
                
                if validated_size == 'UNKNOWN':
                    _company_size_cache[cache_key] = validated_size
                    return validated_size
                
                # Check if it's a valid range or single number
                if '-' in validated_size:
                    try:
                        start, end = validated_size.split('-')
                        if start.isdigit() and end.isdigit():
                            # Ensure start is less than end
                            start_num, end_num = int(start), int(end)
                            if start_num > end_num:
                                start, end = end, start
                            validated_size = f"{start}-{end}"
                            _company_size_cache[cache_key] = validated_size
                            return validated_size
                    except ValueError:
                        pass  # If range is invalid, continue to next check
                
                # Check for single number
                if validated_size.isdigit():
                    _company_size_cache[cache_key] = validated_size
                    return validated_size
                
                _company_size_cache[cache_key] = 'UNKNOWN'
                return 'UNKNOWN'
                
            except Exception as e:
                print(f"OpenAI validation failed: {str(e)}")
                print("Attempting direct OpenAI query...")
                
                try:
                    # Use the same system and format as Perplexity
                    openai_messages = [
                        {
                            'role': 'system',
                            'content': '''You are an expert at finding accurate company information, with access to more comprehensive and up-to-date data than TechCrunch, LinkedIn, or other public sources. Your specialty is determining precise employee counts for companies of any size, from startups to enterprises. You have access to multiple reliable data sources and can cross-reference information to provide the most accurate count possible.'''
                        },
                        {
                            'role': 'user',
                            'content': f'''Find the current or most recent employee count for {company_name}, a company in the {industry} industry. Search thoroughly across all available sources.

Respond ONLY with one of:
- An exact number for verified recent data (e.g., '5000')
- A specific range for approximate data (e.g., '100-150')
- 'UNKNOWN' if no reliable data found

Respond ONLY with the number, range, or UNKNOWN - no other text.'''
                        }
                    ]
                    
                    openai_response = openai_client.chat.completions.create(
                        model="gpt-4",
                        messages=openai_messages,
                        temperature=0
                    )
                    
                    direct_size = openai_response.choices[0].message.content.strip()
                    print(f"OpenAI direct query response: {direct_size}")
                    
                    # Validate the direct response
                    direct_size = direct_size.replace(',', '').replace(' ', '')
                    if direct_size == 'UNKNOWN':
                        _company_size_cache[cache_key] = direct_size
                        return direct_size
                    elif '-' in direct_size:
                        start, end = direct_size.split('-')
                        if start.isdigit() and end.isdigit():
                            _company_size_cache[cache_key] = direct_size
                            return direct_size
                    elif direct_size.isdigit():
                        _company_size_cache[cache_key] = direct_size
                        return direct_size
                    
                    _company_size_cache[cache_key] = 'UNKNOWN'
                    return 'UNKNOWN'
                    
                except Exception as e2:
                    print(f"OpenAI direct query failed: {str(e2)}")
                    print("Both OpenAI attempts failed, returning UNKNOWN")
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
    invalid_count = 0
    
    for idx, row in df.iterrows():
        # Skip if we already have data for this company
        current_size = str(row.get("Size", "")).strip()
        if current_size and current_size.upper() != "NAN":
            print(f"\nSkipping company {idx + 1}/{total_companies} - already has size: {current_size}")
            skipped_count += 1
            continue
        
        # Skip if company name or industry is invalid
        if pd.isna(row[company_col]) or pd.isna(row[industry_col]) or \
           not str(row[company_col]).strip() or not str(row[industry_col]).strip():
            print(f"\nSkipping company {idx + 1}/{total_companies} - invalid data")
            invalid_count += 1
            continue
            
        print(f"\nProcessing company {idx + 1}/{total_companies}")
        df.at[idx, "Size"] = get_company_size(row[company_col], row[industry_col])
        processed_count += 1
        
        # Save after each company
        df.to_excel(excel_path, sheet_name="Original Data", index=False)
        print(f"Saved progress after company {idx + 1}")
    
    print(f"\nCompleted: {processed_count} processed, {skipped_count} skipped (already had data), {invalid_count} skipped (invalid data)")
    
    print(f"Processed {len(df)} companies")
    print("\nFirst few rows with Size:")
    print(df[[company_col, industry_col, "Size"]].head())

if __name__ == "__main__":
    main()
