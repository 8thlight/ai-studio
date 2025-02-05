"""Excel file processor for company data enrichment."""
import pandas as pd
from typing import Tuple
from config import Config

class ExcelProcessor:
    """Handles Excel file operations for company data processing."""
    
    def __init__(self, config: Config):
        """Initialize with configuration."""
        self.config = config
        self.df = None
        self.total_companies = 0
        self.processed_count = 0
        self.skipped_count = 0
        self.invalid_count = 0
    
    def load_and_validate_data(self) -> None:
        """Load and validate the Excel data."""
        self.df = pd.read_excel(self.config.excel_path, sheet_name=self.config.excel_sheet)
        self.total_companies = len(self.df)
        
        print("\nAvailable columns in Excel:")
        for col in self.df.columns:
            print(f"  - {col}")
        
        if self.config.company_column not in self.df.columns or self.config.industry_column not in self.df.columns:
            raise ValueError(
                f"Could not find required columns. Need '{self.config.company_column}' "
                f"and '{self.config.industry_column}' columns."
            )
        
        print(f"\nUsing columns:\n  Company: {self.config.company_column}"
              f"\n  Industry: {self.config.industry_column}")
        
        if self.config.size_column not in self.df.columns:
            print("Adding Size column...")
            self.df[self.config.size_column] = ""
    
    def _should_skip_company(self, row: pd.Series) -> Tuple[bool, str]:
        """Check if company should be skipped and return reason."""
        # Check for existing valid size
        current_size = str(row.get(self.config.size_column, "")).strip()
        if current_size and current_size.upper() != "NAN":
            return True, f"already has size: {current_size}"
        
        # Check for invalid data
        if (pd.isna(row[self.config.company_column]) or 
            pd.isna(row[self.config.industry_column]) or 
            not str(row[self.config.company_column]).strip() or 
            not str(row[self.config.industry_column]).strip()):
            return True, "invalid data"
        
        return False, ""
    
    def process_companies(self, get_company_size_fn) -> None:
        """Process all companies and update their sizes."""
        if self.df is None:
            raise ValueError("Data not loaded. Call load_and_validate_data first.")
        
        for idx, row in self.df.iterrows():
            should_skip, reason = self._should_skip_company(row)
            
            if should_skip:
                print(f"\nSkipping company {idx + 1}/{self.total_companies} - {reason}")
                if "invalid data" in reason:
                    self.invalid_count += 1
                else:
                    self.skipped_count += 1
                continue
            
            print(f"\nProcessing company {idx + 1}/{self.total_companies}")
            self.df.at[idx, self.config.size_column] = get_company_size_fn(
                row[self.config.company_column], 
                row[self.config.industry_column]
            )
            self.processed_count += 1
            
            # Save after each company
            self.save_progress()
            print(f"Saved progress after company {idx + 1}")
    
    def save_progress(self) -> None:
        """Save current progress to Excel file."""
        self.df.to_excel(self.config.excel_path, sheet_name=self.config.excel_sheet, index=False)
    
    def print_summary(self) -> None:
        """Print processing summary and preview data."""
        print(f"\nCompleted: {self.processed_count} processed, "
              f"{self.skipped_count} skipped (already had data), "
              f"{self.invalid_count} skipped (invalid data)")
        print(f"Processed {self.total_companies} companies")
        print("\nFirst few rows with Size:")
        print(self.df[[self.config.company_column, 
                      self.config.industry_column, 
                      self.config.size_column]].head())
