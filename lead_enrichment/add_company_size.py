"""Script to enrich company data with employee size information using AI APIs."""
import os
import json
import time
import requests
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import litellm
from litellm.caching import Cache

from config import Config
from excel_processor import ExcelProcessor

# Load environment variables and initialize config
load_dotenv()
config = Config()

# Setup litellm cache with disk persistence
litellm.cache = Cache(type="disk")

# Ensure cache directory exists
Path(config.cache_path).parent.mkdir(parents=True, exist_ok=True)


def _validate_size_format(size: str) -> Optional[str]:
    """Validate and standardize size format."""
    # Clean the size string
    size = size.replace(',', '').replace(' ', '')
    
    # Handle UNKNOWN case
    if size.upper() == 'UNKNOWN':
        return 'UNKNOWN'
        
    # Handle range format
    if '-' in size:
        try:
            start, end = size.split('-')
            if start.isdigit() and end.isdigit():
                start_num, end_num = int(start), int(end)
                if start_num > end_num:
                    start, end = end, start
                return f"{start}-{end}"
        except ValueError:
            return None
            
    # Handle single number
    if size.isdigit():
        return size
        
    return None

def _query_perplexity(company_name: str, industry: str) -> Optional[str]:
    """Query Perplexity API for company size."""
    api_key = config.perplexity_api_key
    if not api_key:
        raise ValueError("PERPLEXITY_API_KEY environment variable is required")
    
    messages = _create_size_query_messages(company_name, industry)
    
    try:
        response = litellm.completion(
            model=config.perplexity_model,
            messages=messages,
            temperature=config.openai_temperature,  # Use same temperature for consistency
            api_key=api_key,
            api_base=config.perplexity_api_endpoint,
            provider='perplexity',
            caching=True
        )
        
        size = response.choices[0].message.content.strip()
        print(f"Perplexity Response: {size}")
        return _validate_size_format(size)
        
    except Exception as e:
        print(f"Exception when querying Perplexity: {str(e)}")
        return None

def _query_openai(company_name: str, industry: str) -> Optional[str]:
    """Query OpenAI API for company size."""
    try:
        messages = _create_size_query_messages(company_name, industry)
        response = litellm.completion(
            model=config.openai_model,
            messages=messages,
            temperature=config.openai_temperature,
            api_key=config.openai_api_key,
            caching=True
        )
        
        size = response.choices[0].message.content.strip()
        print(f"OpenAI Response: {size}")
        return _validate_size_format(size)
        
    except Exception as e:
        print(f"OpenAI query failed: {str(e)}")
        return None

def _create_size_query_messages(company_name: str, industry: str) -> list[Dict[str, str]]:
    """Create message list for API queries."""
    return [
        {
            'role': 'system',
            'content': config.openai_system_prompt
        },
        {
            'role': 'user',
            'content': config.company_size_user_prompt.format(company_name=company_name, industry=industry)
        }
    ]

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

    api_key = config.perplexity_api_key
    if not api_key:
        raise ValueError("PERPLEXITY_API_KEY environment variable is required")

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    messages = [
        {
            'role': 'system',
            'content': config.perplexity_system_prompt
        },
        {
            'role': 'user',
            'content': config.company_size_user_prompt.format(company_name=company_name, industry=industry)
        }
    ]
    
    print(f"\nQuerying for: {company_name} ({industry})")
    print("System prompt and user message prepared for query")
    
    try:
        response = litellm.completion(
            model=config.perplexity_model,
            messages=messages,
            temperature=config.openai_temperature,  # Use same temperature for consistency
            api_key=api_key,
            api_base=config.perplexity_api_endpoint,
            provider='perplexity',
            caching=True
        )
        
        size = response.choices[0].message.content.strip()
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
                        'content': config.openai_system_prompt
                    },
                    {
                        'role': 'user',
                        'content': config.company_size_user_prompt.format(company_name=company_name, industry=industry)
                    }
                ]
                
                openai_response = litellm.completion(
                    model=config.openai_model,
                    messages=openai_messages,
                    temperature=config.openai_temperature,
                    api_key=config.openai_api_key,
                    caching=True
                )
                
                openai_size = openai_response.choices[0].message.content.strip()
                print(f"OpenAI Response: {openai_size}")
                
                # Validate OpenAI's response directly
                openai_size = openai_size.replace(',', '').replace(' ', '')
                if openai_size == 'UNKNOWN':
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
                            return openai_size
                    except ValueError:
                        pass
                
                if openai_size.isdigit():
                    return openai_size
                    
                return 'UNKNOWN'
                
            except Exception as e:
                print(f"OpenAI query failed: {str(e)}")
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
                'content': config.validation_system_prompt
            },
            {
                'role': 'user',
                'content': config.validation_user_prompt.format(size=cleaned_size, company_name=company_name, industry=industry)
            }
        ]
        
        try:
            validation = litellm.completion(
                model=config.openai_model,
                messages=validation_messages,
                temperature=config.openai_temperature,
                api_key=config.openai_api_key,
                caching=True
            )
            
            validated_size = validation.choices[0].message.content.strip()
            print(f"OpenAI Validation: {validated_size}")
            
            # Clean up the validated response
            validated_size = validated_size.replace(',', '').replace(' ', '')
            
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
                        return validated_size
                except ValueError:
                    pass  # If range is invalid, continue to next check
            
            # Check for single number
            if validated_size.isdigit():
                return validated_size
            
            return 'UNKNOWN'
            
        except Exception as e:
            print(f"OpenAI validation failed: {str(e)}")
            print("Attempting direct OpenAI query...")
            
            try:
                # Use the same system and format as Perplexity
                openai_messages = [
                    {
                        'role': 'system',
                        'content': config.openai_system_prompt
                    },
                    {
                        'role': 'user',
                        'content': config.company_size_user_prompt.format(company_name=company_name, industry=industry)
                    }
                ]
                
                openai_response = litellm.completion(
                    model=config.openai_model,
                    messages=openai_messages,
                    temperature=config.openai_temperature,
                    api_key=config.openai_api_key,
                    caching=True
                )
                
                direct_size = openai_response.choices[0].message.content.strip()
                print(f"OpenAI direct query response: {direct_size}")
                
                # Validate the direct response
                direct_size = direct_size.replace(',', '').replace(' ', '')
                if '-' in direct_size:
                    start, end = direct_size.split('-')
                    if start.isdigit() and end.isdigit():
                        return direct_size
                elif direct_size.isdigit():
                    return direct_size
                
                return 'UNKNOWN'
                
            except Exception as e2:
                print(f"OpenAI direct query failed: {str(e2)}")
                print("Both OpenAI attempts failed, returning UNKNOWN")
                return 'UNKNOWN'
        else:
            print(f"Error with API call for {company_name}: {response.status_code}")
            return 'UNKNOWN'
            
    except Exception as e:
        print(f"Exception when processing {company_name}: {str(e)}")
        return 'UNKNOWN'
    
    # Add a small delay to avoid hitting rate limits
    time.sleep(config.rate_limit_delay)



def main():
    """Main entry point for the script."""
    # Initialize Excel processor
    processor = ExcelProcessor(config)
    
    # Load and process data
    processor.load_and_validate_data()
    processor.process_companies(get_company_size)
    
    # Print summary
    processor.print_summary()

if __name__ == "__main__":
    main()
