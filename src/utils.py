import os
import re

def create_markdown_dir(date):
    """Create directory for the year and month if they don't exist"""
    year = date.year
    month = date.strftime('%m-%B')  # e.g., "01-January"
    year_dir = f"orders/{year}"
    month_dir = f"{year_dir}/{month}"
    
    os.makedirs(month_dir, exist_ok=True)
    return month_dir

def clean_filename(title):
    """Convert title to valid filename"""
    return re.sub(r'[^\\w\s-]', '', title).strip().lower().replace(' ', '-')

def get_headers():
    """Get headers to mimic a browser request"""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json',
    }