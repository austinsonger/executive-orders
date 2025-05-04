#!/usr/bin/env python3
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil import parser
import re
import time

def create_markdown_dir(date):
    """Create directory for the year and month if they don't exist"""
    base_dir = "rules_and_regulations"  # Relative path to the output directory
    year = date.year
    month = date.strftime('%m-%B')  # e.g., "01-January"
    year_dir = f"{base_dir}/{year}"
    month_dir = f"{year_dir}/{month}"
    
    if not os.path.exists(year_dir):
        os.makedirs(year_dir)
    if not os.path.exists(month_dir):
        os.makedirs(month_dir)
    return month_dir

def clean_filename(title):
    """Convert title to valid filename"""
    return re.sub(r'[^\w\s-]', '', title).strip().lower().replace(' ', '-')

def get_headers():
    """Get headers to mimic a browser request"""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json',
    }

def fetch_all_pages(base_url, params):
    """Fetch all pages of results from the Federal Register API."""
    all_results = []
    page = 1
    total_pages = None

    while True:
        params['page'] = page
        try:
            print(f"Fetching page {page}...")
            response = requests.get(base_url, params=params, headers=get_headers(), timeout=30)
            response.raise_for_status()
            data = response.json()

            if total_pages is None:
                total_pages = data.get('total_pages', 1)
                total_results = data.get('count', 0)
                print(f"Found {total_results} total results across {total_pages} pages")

            results = data.get('results', [])
            if not results:
                break

            all_results.extend(results)

            if page >= total_pages:
                break

            page += 1
            time.sleep(1)  # Be polite to the API

        except Exception as e:
            print(f"Error fetching page {page}: {e}")
            break

    return all_results

def save_as_markdown(rule, content):
    """Save the rule or regulation as a markdown file."""
    # Create directory path using the date
    dir_path = create_markdown_dir(rule['date'])

    # Create filename from date and sanitized title
    date_str = rule['date'].strftime('%Y-%m-%d')
    clean_title = clean_filename(rule['title'])
    filename = f"{date_str}-{clean_title}.md"
    filepath = os.path.join(dir_path, filename)

    markdown_content = f"""# {rule['title']}

## Summary

**Date:** {rule['date'].strftime('%B %d, %Y')}

**Document Details:**
- Document Number: {rule.get('document_number', 'N/A')}
- Type: {rule.get('type', 'N/A')}
- Citation: {rule.get('citation', 'N/A')}

## Sources
- [Federal Register]({rule['link']})

---

## Content

{content}

---

*Filed by the Office of the Federal Register on {rule['date'].strftime('%B %d, %Y')}*
"""

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print(f"Saved: {filepath}")
        return True
    except Exception as e:
        print(f"Error saving file: {e}")
        return False

def scrape_rules_and_regulations():
    """Fetch rules and regulations from Federal Register API"""
    base_url = "https://www.federalregister.gov/api/v1/documents"
    
    # Parameters for the Federal Register API
    params = {
        'conditions[correction]': '0',
        'conditions[type][]': ['RULE', 'PRORULE', 'INTLRULE'],  # Final Rules, Proposed Rules, Interim Rules
        'conditions[publication_date][gte]': '2025-01-01',  # Adjust date as needed
        'fields[]': [
            'citation',
            'document_number',
            'end_page',
            'html_url',
            'pdf_url',
            'type',
            'subtype',
            'publication_date',
            'start_page',
            'title',
            'disposition_notes',
            'full_text_xml_url',
            'body_html_url',
            'json_url'
        ],
        'per_page': 1000,
        'order': 'publication_date',
        'format': 'json'
    }
    
    print("Fetching rules and regulations from Federal Register API...")
    results = fetch_all_pages(base_url, params)
    print(f"Retrieved {len(results)} total results")
    
    for result in results:
        try:
            title = result.get('title', '').strip()
            date_str = result.get('publication_date')
            html_url = result.get('html_url')
            document_number = result.get('document_number')
            rule_type = result.get('type')
            citation = result.get('citation')

            if not all([title, date_str, html_url]):
                print(f"Skipping incomplete rule: {title}")
                continue

            date = parser.parse(date_str)

            rule = {
                'title': title,
                'date': date,
                'link': html_url,
                'document_number': document_number,
                'type': rule_type,
                'citation': citation
            }

            # Check if the file already exists
            dir_path = create_markdown_dir(rule['date'])
            date_str = rule['date'].strftime('%Y-%m-%d')
            clean_title = clean_filename(rule['title'])
            filename = f"{date_str}-{clean_title}.md"
            filepath = os.path.join(dir_path, filename)

            if os.path.exists(filepath):
                print(f"Rule already exists, skipping: {rule['title']} ({rule['date']})")
                continue

            # Fetch and save the rule content
            print(f"Processing rule: {rule['title']} ({rule['date']})")
            content = f"Content for {rule['title']} is available at {rule['link']}."
            save_as_markdown(rule, content)

        except Exception as e:
            print(f"Error processing rule: {e}")

    print("Scraping rules and regulations complete.")

if __name__ == "__main__":
    scrape_rules_and_regulations()