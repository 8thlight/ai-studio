"""Configuration settings for the lead enrichment application."""
from dataclasses import dataclass

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
    perplexity_model: str = "sonar"
    perplexity_system_prompt: str = '''You are an expert at finding accurate company information, with access to more comprehensive and up-to-date data than TechCrunch, LinkedIn, or other public sources. Your specialty is determining precise employee counts for companies of any size, from startups to enterprises. You have access to multiple reliable data sources and can cross-reference information to provide the most accurate count possible.'''
    
    # OpenAI settings
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.2
    
    # Common settings
    rate_limit_delay: float = 0.5
