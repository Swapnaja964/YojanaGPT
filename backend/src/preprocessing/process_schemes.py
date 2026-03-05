import os
import re
import uuid
import pandas as pd
import pdfplumber
from bs4 import BeautifulSoup
import chardet
from langdetect import detect
from googletrans import Translator
from datetime import datetime
from typing import Dict, Tuple, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SchemeProcessor:
    def __init__(self, csv_path: str, raw_docs_dir: str = 'raw_docs'):
        """
        Initialize the SchemeProcessor with CSV path and raw documents directory.
        
        Args:
            csv_path: Path to the input CSV file
            raw_docs_dir: Directory containing raw documents (PDFs/HTML)
        """
        self.csv_path = csv_path
        self.raw_docs_dir = raw_docs_dir
        self.translator = Translator()
        
        # Define required output columns
        self.output_columns = [
            'scheme_id', 'scheme_name', 'description_raw', 'benefits_raw',
            'eligibility_raw', 'process_raw', 'state_scope', 'category',
            'source_url', 'last_updated', 'synthesized_fields'
        ]
    
    def detect_file_encoding(self, file_path: str) -> str:
        """Detect the encoding of a file."""
        with open(file_path, 'rb') as f:
            raw_data = f.read(10000)  # Read first 10KB to detect encoding
        return chardet.detect(raw_data)['encoding']
    
    def load_csv(self) -> pd.DataFrame:
        """Load the CSV file into a pandas DataFrame."""
        try:
            # Try to detect encoding
            encoding = self.detect_file_encoding(self.csv_path)
            df = pd.read_csv(self.csv_path, encoding=encoding, on_bad_lines='warn')
            logger.info(f"Successfully loaded CSV with {len(df)} rows")
            return df
        except Exception as e:
            logger.error(f"Error loading CSV: {str(e)}")
            raise
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if pd.isna(text):
            return ""
        
        # Convert to string if not already
        text = str(text)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # Replace non-ASCII quotes and dashes
        text = text.replace('"', '"')
        text = text.replace("'", "'")
        text = text.replace('–', '-')
        text = text.replace('—', '-')
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        # Truncate if too long
        if len(text) > 6000:
            text = text[:5997] + '...'
            
        return text.strip()
    
    def detect_language(self, text: str) -> str:
        """Detect the language of the text."""
        try:
            return detect(text)
        except:
            return 'en'  # Default to English if detection fails
    
    def translate_to_english(self, text: str, src_lang: str) -> str:
        """Translate text to English if it's not already in English."""
        if not text or src_lang == 'en':
            return text
            
        try:
            translated = self.translator.translate(text, src=src_lang, dest='en')
            return translated.text
        except Exception as e:
            logger.warning(f"Translation failed: {str(e)}")
            return text  # Return original if translation fails
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from a PDF file."""
        try:
            text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
            return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF {file_path}: {str(e)}")
            return ""
    
    def extract_text_from_html(self, file_path: str) -> str:
        """Extract text from an HTML file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                soup = BeautifulSoup(f, 'html.parser')
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                return soup.get_text(separator=' ', strip=True)
        except Exception as e:
            logger.error(f"Error extracting text from HTML {file_path}: {str(e)}")
            return ""
    
    def find_matching_document(self, scheme_name: str, source_url: str = None) -> Optional[str]:
        """Find a matching document in the raw_docs directory."""
        if not os.path.exists(self.raw_docs_dir):
            return None
            
        # Try to find by URL first
        if source_url:
            # Extract filename from URL
            url_filename = os.path.basename(source_url)
            if url_filename:
                for ext in ['.pdf', '.html', '.htm']:
                    doc_path = os.path.join(self.raw_docs_dir, url_filename + ext)
                    if os.path.exists(doc_path):
                        return doc_path
        
        # Try to find by scheme name
        safe_name = re.sub(r'[^\w\s-]', '', scheme_name).strip().lower()
        if not safe_name:
            return None
            
        for filename in os.listdir(self.raw_docs_dir):
            # Check if scheme name is in filename (case insensitive)
            if safe_name in filename.lower():
                return os.path.join(self.raw_docs_dir, filename)
                
        return None
    
    def extract_text_from_document(self, file_path: str) -> str:
        """Extract text from a document based on its extension."""
        if not file_path or not os.path.exists(file_path):
            return ""
            
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif ext in ['.html', '.htm']:
            return self.extract_text_from_html(file_path)
        else:
            logger.warning(f"Unsupported file format: {file_path}")
            return ""
    
    def synthesize_missing_fields(self, row: dict) -> Tuple[dict, list]:
        """Synthesize missing description or benefits if needed."""
        synthesized = []
        
        # Check if we need to synthesize description
        if not row.get('description_raw') and (row.get('eligibility_raw') or row.get('process_raw')):
            eligibility = row.get('eligibility_raw', '')
            process = row.get('process_raw', '')
            row['description_raw'] = f"This scheme provides benefits to eligible individuals. {eligibility[:200]} {process[:200]}".strip()
            synthesized.append('description_raw')
        
        # Check if we need to synthesize benefits
        if not row.get('benefits_raw') and (row.get('eligibility_raw') or row.get('description_raw')):
            eligibility = row.get('eligibility_raw', '')
            description = row.get('description_raw', '')
            row['benefits_raw'] = f"Benefits include: {description[:200]} {eligibility[:200]}".strip()
            synthesized.append('benefits_raw')
        
        return row, synthesized
    
    def process_scheme(self, row: dict) -> dict:
        """Process a single scheme row."""
        # Initialize with default values
        scheme = {
            'scheme_id': str(uuid.uuid4()),
            'synthesized_fields': []
        }
        
        # Map input fields to output fields
        field_mapping = {
            'scheme_name': 'scheme_name',
            'description': 'description_raw',
            'benefits': 'benefits_raw',
            'eligibility': 'eligibility_raw',
            'process': 'process_raw',
            'state_scope': 'state_scope',
            'category': 'category',
            'source_url': 'source_url',
            'last_updated': 'last_updated'
        }
        
        # Map and clean fields
        for input_field, output_field in field_mapping.items():
            if input_field in row and pd.notna(row[input_field]):
                scheme[output_field] = self.clean_text(row[input_field])
            else:
                scheme[output_field] = ""
        
        # Try to find and extract text from matching document if key fields are missing
        if not any(scheme.get(f) for f in ['description_raw', 'benefits_raw', 'eligibility_raw']):
            doc_path = self.find_matching_document(
                scheme.get('scheme_name', ''),
                scheme.get('source_url', '')
            )
            
            if doc_path:
                doc_text = self.extract_text_from_document(doc_path)
                if doc_text:
                    # Use the first 2000 chars as description if empty
                    if not scheme.get('description_raw'):
                        scheme['description_raw'] = self.clean_text(doc_text[:2000])
                        scheme['synthesized_fields'].append('description_raw')
                    
                    # Use next 2000 chars as benefits if empty
                    if not scheme.get('benefits_raw') and len(doc_text) > 2000:
                        scheme['benefits_raw'] = self.clean_text(doc_text[2000:4000])
                        scheme['synthesized_fields'].append('benefits_raw')
        
        # Synthesize missing fields if needed
        scheme, new_synthesized = self.synthesize_missing_fields(scheme)
        scheme['synthesized_fields'].extend(new_synthesized)
        
        # Apply fallback rules for missing fields
        if not scheme.get('description_raw'):
            scheme['description_raw'] = "Summary unavailable; this scheme provides benefits to eligible residents."
            scheme['synthesized_fields'].append('description_raw')
        
        if not scheme.get('benefits_raw'):
            scheme['benefits_raw'] = "Benefits described by the scheme: financial or non-financial assistance."
            scheme['synthesized_fields'].append('benefits_raw')
            
        if not scheme.get('eligibility_raw'):
            scheme['eligibility_raw'] = "Eligibility: Indian residents meeting scheme-specific requirements."
            scheme['synthesized_fields'].append('eligibility_raw')
        
        # Ensure all text fields are within length limits
        for field in ['description_raw', 'benefits_raw', 'eligibility_raw', 'process_raw']:
            if field in scheme and len(scheme[field]) > 6000:
                scheme[field] = scheme[field][:5997] + '...'
        
        # Convert synthesized_fields to comma-separated string
        scheme['synthesized_fields'] = ','.join(sorted(set(scheme['synthesized_fields'])))
        
        return scheme
    
    def validate_output(self, df: pd.DataFrame) -> bool:
        """Validate the output DataFrame meets requirements."""
        # Check required fields
        if 'scheme_id' not in df.columns or 'scheme_name' not in df.columns:
            logger.error("Missing required columns: scheme_id or scheme_name")
            return False
        
        # Check for null scheme_id or scheme_name
        if df['scheme_id'].isnull().any() or df['scheme_name'].isnull().any():
            logger.error("Found null values in scheme_id or scheme_name")
            return False
        
        # Check at least 90% of rows have non-empty eligibility_raw
        elig_ratio = df['eligibility_raw'].str.strip().astype(bool).mean()
        if elig_ratio < 0.9:
            logger.warning(f"Only {elig_ratio*100:.1f}% of rows have non-empty eligibility_raw (below 90%)")
        
        # Check text field lengths
        text_fields = ['description_raw', 'benefits_raw', 'eligibility_raw', 'process_raw']
        for field in text_fields:
            if field in df.columns:
                too_long = df[field].str.len() > 6000
                if too_long.any():
                    logger.warning(f"Found {too_long.sum()} rows with {field} exceeding 6000 characters")
        
        return True
    
    def process(self, output_path: str = 'backend/data/processed/schemes_cleaned.parquet') -> bool:
        """Process the schemes and save the output."""
        try:
            # Load and process data
            logger.info("Loading input CSV...")
            df = self.load_csv()
            
            if df.empty:
                logger.error("Input CSV is empty")
                return False
            
            # Process each row
            logger.info(f"Processing {len(df)} schemes...")
            processed_schemes = []
            for _, row in df.iterrows():
                try:
                    scheme = self.process_scheme(row)
                    processed_schemes.append(scheme)
                except Exception as e:
                    logger.error(f"Error processing row {_}: {str(e)}")
            
            # Create output DataFrame
            output_df = pd.DataFrame(processed_schemes)
            
            # Ensure all required columns exist
            for col in self.output_columns:
                if col not in output_df.columns:
                    output_df[col] = ""
            
            # Reorder columns
            output_df = output_df[self.output_columns]
            
            # Validate output
            if not self.validate_output(output_df):
                logger.error("Output validation failed")
                return False
            
            # Save to parquet
            logger.info(f"Saving to {output_path}...")
            output_df.to_parquet(output_path, index=False)
            logger.info("Processing completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Processing failed: {str(e)}", exc_info=True)
            return False


def main():
    # Initialize processor
    processor = SchemeProcessor(
        csv_path='backend/data/raw/myscheme_data.csv',
        raw_docs_dir='raw_docs'
    )
    
    # Process and save
    success = processor.process('backend/data/processed/schemes_cleaned.parquet')
    
    if success:
        print("Processing completed successfully. Output saved to 'backend/data/processed/schemes_cleaned.parquet'")
        return 0
    else:
        print("Processing failed. Check the logs for details.")
        return 1


def display_processed_data():
    try:
        df = pd.read_parquet("backend/data/processed/schemes_cleaned.parquet")
        print("\nFirst few rows of the processed data:")
        print(df.head())
        print("\nData types:")
        print(df.dtypes)
        print(f"\nTotal number of records: {len(df)}")
    except Exception as e:
        print(f"\nError displaying data: {str(e)}")

if __name__ == "__main__":
    import sys
    # Run the main processing
    result = main()
    
    # Display the processed data
    display_processed_data()
    
    # Exit with the result code from main()
    sys.exit(result)
