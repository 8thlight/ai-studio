"""Configuration settings for the lead enrichment application."""
from dataclasses import dataclass
from typing import Optional
import os

@dataclass
class Config:
    """Application configuration settings."""
    # Excel settings
    excel_path: str = "data/hubspot-crm-exports-ai-nurture-test-updated.xlsx"
    excel_sheet: str = "Original Data"
    company_column: str = "Company name"
    industry_column: str = "Cleaned Industry"
    size_column: str = "Size"
    
    # Perplexity settings
    perplexity_api_endpoint: str = "https://api.perplexity.ai"
    perplexity_model: str = "perplexity/sonar"
    perplexity_system_prompt: str = '''You are an expert at finding accurate company information, with access to more comprehensive and up-to-date data than TechCrunch, LinkedIn, or other public sources. Your specialty is determining precise employee counts for companies of any size, from startups to enterprises. You have access to multiple reliable data sources and can cross-reference information to provide the most accurate count possible.'''
    
    # LLM settings
    cache_path: str = "cache/llm_responses.json"  # Path to store litellm cache
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.2
    openai_system_prompt: str = perplexity_system_prompt  # Use same prompt for consistency
    
    # Common LLM prompts
    company_size_user_prompt: str = '''Find the current or most recent employee count for {company_name}, a company in the {industry} industry. Search thoroughly across all available sources.

Respond ONLY with one of:
- An exact number for verified recent data (e.g., '5000')
- A specific range for approximate data (e.g., '100-150')
- 'UNKNOWN' if no reliable data found

Respond ONLY with the number, range, or UNKNOWN - no other text.'''
    
    # Validation prompts
    validation_system_prompt: str = '''You are a data validation expert who extracts employee counts from text. Your task is to:
1. Find any numbers that represent employee counts, even if they are embedded in text (e.g. "More than 458,000" -> "458000")
2. If multiple numbers are found, use the most specific/recent one
3. Handle ranges (e.g. "100-150") and keep them as is
4. Remove any commas from numbers
5. Return UNKNOWN only if no valid numbers can be found

Respond ONLY with the cleaned number/range or UNKNOWN.'''
    
    validation_user_prompt: str = '''Validate this company size response: "{size}"

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
    
    # Common settings
    rate_limit_delay: float = 0.05
    
    @property
    def perplexity_api_key(self) -> Optional[str]:
        """Get Perplexity API key from environment variables."""
        return os.getenv('PERPLEXITY_API_KEY')
    
    @property
    def openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key from environment variables."""
        return os.getenv('OPENAI_API_KEY')
