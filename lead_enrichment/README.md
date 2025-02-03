# Lead Enrichment Tool

This tool enriches company data by determining company sizes using the Perplexity API.

## Setup

1. **Get Perplexity API Key**
   - Go to [Perplexity API](https://docs.perplexity.ai/docs/getting-started)
   - Sign up or log in to get your API key
   - Copy your API key

2. **Create .env file**
   Create a `.env` file in the project root directory and add your API key:
   ```
   PERPLEXITY_API_KEY=your-api-key-here
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
1. Read the Excel file from the data directory. E.g. `data/companies.xlsx`
2. Query Perplexity API to get employee counts for each company
3. Add the results as a new "Size" column
4. Save the updated data back to the Excel file
