# Lead Enrichment Tool

This tool enriches company data by determining company sizes using the Perplexity API with OpenAI validation.

## Features

- **Dual AI Processing**: Uses Perplexity API for initial company size lookup and GPT-4 for validation
- **Smart Caching**: In-memory cache to avoid duplicate API calls
- **Incremental Processing**: Saves progress after each company
- **Data Validation**: OpenAI validates and standardizes company size data
- **Robust Error Handling**: Fallback validation if OpenAI is unavailable

## Setup

1. **Get API Keys**
   - Get a [Perplexity API Key](https://docs.perplexity.ai/docs/getting-started)
   - Get an [OpenAI API Key](https://platform.openai.com/api-keys)

2. **Create .env file**
   Create a `.env` file in the project root directory and add your API keys:
   ```
   PERPLEXITY_API_KEY=your-perplexity-key-here
   OPENAI_API_KEY=your-openai-key-here
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the script:
```bash
python add_company_size.py
```

The script will:
1. Read the Excel file from `data/hubspot-crm-exports-ai-nurture-test-updated.xlsx`
2. Process each company:
   - Check cache for existing results
   - Query Perplexity API for employee count
   - Validate and standardize data with OpenAI
   - Save after each successful lookup
3. Skip companies that:
   - Already have size data
   - Have invalid/missing company name or industry
4. Add results in the "Size" column as either:
   - Exact number (e.g., "5000")
   - Range (e.g., "100-150")
   - "UNKNOWN" if no reliable data found

## Response Format

Company sizes are standardized to:
- **Exact Numbers**: When precise data is available (e.g., "5000")
- **Ranges**: When approximate data is available (e.g., "100-150")
- **UNKNOWN**: When no reliable data can be found

## Error Handling

- Caches successful lookups to avoid duplicate API calls
- Falls back to basic validation if OpenAI validation fails
- Skips invalid entries while continuing to process others
- Saves progress frequently to prevent data loss
