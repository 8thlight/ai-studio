import pandas as pd
import os
import requests
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_company_size(company_name: str, industry: str) -> str:
    """
    Query Perplexity API to determine company size based on name and industry.
    Returns the number of employees as a range (e.g., "100-150") or single number (e.g., "5000")
    If unable to determine, returns "UNKNOWN"
    """
    api_key = os.getenv('PERPLEXITY_API_KEY')
    if not api_key:
        raise ValueError("PERPLEXITY_API_KEY environment variable is required")

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    prompt = f'''For the company '{company_name}' in the '{industry}' industry, what is their employee count? Respond with ONLY:
    - A specific number if known (e.g., '5000')
    - A range if approximate (e.g., '100-150')
    - 'UNKNOWN' if you cannot determine
    No other text or explanation - just the number, range, or UNKNOWN.'''
    
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
                return size
            
            # Check if it's a valid range (e.g., 100-150) or single number
            if '-' in size:
                start, end = size.split('-')
                if start.isdigit() and end.isdigit():
                    return size
            elif size.isdigit():
                return size
            
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
    # Read the Excel file
    excel_path = "hubspot-crm-exports-ai-nurture-test-updated.xlsx"
    df = pd.read_excel(excel_path, sheet_name="Original Data")
    
    # Add Size column
    df["Size"] = df.apply(lambda row: get_company_size(row["Company Name"], row["Cleaned Industry"]), axis=1)
    
    # Save the updated Excel file with the new Size column
    df.to_excel(excel_path, sheet_name="Original Data", index=False)
    
    print(f"Processed {len(df)} companies")
    print("\nFirst few rows with Size:")
    print(df[["Company Name", "Cleaned Industry", "Size"]].head())

if __name__ == "__main__":
    main()
