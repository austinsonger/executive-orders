#!/usr/bin/env python3
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dateutil import parser
import re
import time
import json
import sys
from urllib.parse import urljoin

LAST_CHECK_FILE = 'last_check.txt'

def create_markdown_dir(date, president_name):
    """Create directory for the president, year, and month if they don't exist"""
    base_dir = "Presidential_Executive_Orders"  # Base directory
    president_dir = f"{base_dir}/{president_name}"  # Directory for the president
    year = date.year
    month = date.strftime('%m-%B')  # e.g., "01-January"
    year_dir = f"{president_dir}/{year}"
    month_dir = f"{year_dir}/{month}"
    
    if not os.path.exists(president_dir):
        os.makedirs(president_dir)
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

def get_xml_content(xml_url):
    """Fetch and parse XML content from the Federal Register"""
    try:
        print(f"Fetching XML content from: {xml_url}")
        response = requests.get(xml_url, headers=get_headers(), timeout=30)
        response.raise_for_status()
        
        # Parse XML content
        xml_content = response.content
        soup = BeautifulSoup(xml_content, 'xml')
        
        # Extract the full text content
        content_elements = soup.find_all(['PREAMB', 'TEXT', 'CONTENTS', 'EXECORD', 'SUBJECT', 'AGENCY', 'AGY', 'TITLE', 'FTNT'])
        
        if not content_elements:
            print("No content elements found in XML")
            return None
            
        # Combine all content elements
        full_content = []
        for element in content_elements:
            text = element.get_text(separator='\n\n')
            text = re.sub(r'\n\s*\n', '\n\n', text)
            text = re.sub(r'^\s+', '', text, flags=re.MULTILINE)
            full_content.append(text.strip())
        
        return '\n\n'.join(full_content)
        
    except Exception as e:
        print(f"Error fetching XML content: {str(e)}")
        return None

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

def scrape_historical_orders():
    """Fetch executive orders from Federal Register API"""
    base_url = "https://www.federalregister.gov/api/v1/documents"
    
    # Parameters for the Federal Register API
    params = {
        'conditions[correction]': '0',
        'conditions[type][]': 'PRESDOCU',
        'conditions[presidential_document_type]': 'executive_order',
        'conditions[signing_date][gte]': '2025-01-20',
        'conditions[publication_date][gte]': '2025-01-20',
        'fields[]': [
            'citation',
            'document_number',
            'end_page',
            'html_url',
            'pdf_url',
            'type',
            'subtype',
            'publication_date',
            'signing_date',
            'start_page',
            'title',
            'disposition_notes',
            'executive_order_number',
            'full_text_xml_url',
            'body_html_url',
            'json_url'
        ],
        'per_page': 1000,
        'order': 'document_number',
        'format': 'json'
    }
    
    print("Fetching orders from Federal Register API...")
    results = fetch_all_pages(base_url, params)
    print(f"Retrieved {len(results)} total results")
    
    orders = []
    for result in results:
        try:
            title = result.get('title', '').strip()
            date_str = result.get('signing_date') or result.get('publication_date')
            html_url = result.get('html_url')
            xml_url = result.get('full_text_xml_url')
            document_number = result.get('document_number')
            eo_number = result.get('executive_order_number')
            citation = result.get('citation')
            
            if not all([title, date_str, html_url]):
                print(f"Skipping incomplete order: {title}")
                continue
            
            date = parser.parse(date_str)
            
            # Add EO number to title if available
            if eo_number and not title.startswith(f"Executive Order {eo_number}"):
                title = f"Executive Order {eo_number}: {title}"
            
            orders.append({
                'title': title,
                'date': date,
                'link': html_url,
                'xml_url': xml_url,
                'document_number': document_number,
                'eo_number': eo_number,
                'citation': citation
            })
            print(f"Found order: {title} ({date_str})")
            
        except Exception as e:
            print(f"Error processing order: {str(e)}")
            continue
    
    return orders

def get_order_content(order):
    """Get the content of an executive order, prioritizing XML if available."""
    if order.get('xml_url'):
        try:
            print(f"Fetching XML content from: {order['xml_url']}")
            response = requests.get(order['xml_url'], headers=get_headers(), timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'xml')

            # Extract the full text content from XML
            content_elements = soup.find_all(['PREAMB', 'TEXT', 'CONTENTS', 'EXECORD', 'SUBJECT', 'AGENCY', 'AGY', 'TITLE', 'FTNT'])
            if not content_elements:
                print("No content elements found in XML")
                return None

            # Combine all content elements
            full_content = []
            for element in content_elements:
                text = element.get_text(separator='\n\n')
                text = re.sub(r'\n\s*\n', '\n\n', text)
                text = re.sub(r'^\s+', '', text, flags=re.MULTILINE)
                full_content.append(text.strip())

            return '\n\n'.join(full_content)

        except Exception as e:
            print(f"Error fetching XML content: {e}")
            return None

    print("No XML URL provided or failed to fetch XML content.")
    return None

def format_content(content):
    """Format the executive order content with proper markdown styling"""
    # Clean up the content first
    formatted = content.strip()
    
    # Format the preamble section
    preamble_pattern = r'Title 3—\s*The President\s*Executive Order (\d+) of ([^\n]+)\n([^\n]+)\s*By the authority'
    preamble_replacement = r'''## Preamble

**Title 3—The President**  
**Executive Order \1 of \2**  
**\3**

By the authority'''
    
    formatted = re.sub(preamble_pattern, preamble_replacement, formatted)
    
    # Clean up the authority section spacing and format
    formatted = re.sub(r'By the authority([^:]+):', r'''### Authority

By the authority\1:''', formatted)
    
    # Create list of common section titles to bold
    title_words = [
        "Purpose",
        "Policy",
        "Reinstatement of Prior Administration Policy",
        "Amendments to Prior Administration Policy",
        "Conforming Regulatory Changes",
        "Reg",
        "Additional Positions for Consideration",
        "Revocation",
        "General Provisions",
        "Implementation",
        "Enforcement",
        "Definitions",
        "Scope",
        "Authority",
        "Effective Date",
        "Amendments",
        "Review",
        "Compliance",
        "Administration",
        "Oversight"
    ]
    
    # Format main section headers with bold titles on new line
    def bold_section_title(match):
        section_num = match.group(1)
        title = match.group(2).strip()
        
        # Check if any of the title words appear in the section title
        for word in title_words:
            if word.lower() in title.lower():
                # Replace the word with its bold version, maintaining original case
                original_word = re.search(rf'{word}', title, re.IGNORECASE).group(0)
                # Remove the word from the section header and put it bold on next line
                title = title.replace(original_word, "").strip()
                return f"### Section {section_num}.\n\n**{original_word}**\n"
        
        # If no special word found, just return the normal header
        return f"### Section {section_num}. {title}"
    
    # Apply section header formatting
    formatted = re.sub(r'(?m)^(?:Sec\.|Section)\s*(\d+)\s*\.\s*([^\.]+)\.?', bold_section_title, formatted)
    
    # Fix the custom title pattern to avoid look-behind
    custom_title_pattern = r'(\n### Section \d+\.\n\n)([^\n]+):'
    formatted = re.sub(custom_title_pattern, r'\1**\2**\n', formatted)
    
    # Add proper spacing between paragraphs
    sentences = formatted.split('. ')
    formatted = '. '.join(sentences)
    formatted = re.sub(r'(?<=[.!?])\s+(?=[A-Z])', r'\n\n', formatted)
    
    # Format subsections with letters and ensure proper spacing
    formatted = re.sub(r'\n\s*\(([a-z])\)\s*', r'\n\n(\1) ', formatted)
    
    # Format roman numeral subsections with proper indentation
    formatted = re.sub(r'\n\s*\(([ivxIVX]+)\)\s*', r'\n    (\1) ', formatted)
    
    # Format numbered subsections with proper indentation
    formatted = re.sub(r'\n\s*\((\d+)\)\s*', r'\n    (\1) ', formatted)
    
    # Ensure proper spacing between sections
    formatted = re.sub(r'\n{3,}', r'\n\n', formatted)
    formatted = re.sub(r'(### [^\n]+)\n(?!\n)', r'\1\n\n', formatted)
    
    # Fix any instances where paragraph breaks were added incorrectly
    formatted = re.sub(r'(\n\n)\s*\n+', r'\1', formatted)
    
    # Ensure proper spacing after section headers
    formatted = re.sub(r'(### [^\n]+)\n(?!\n)', r'\1\n\n', formatted)
    
    # Clean up any remaining whitespace issues
    formatted = re.sub(r'(?m)^\s+$', '', formatted)
    
    return formatted

def save_as_markdown(order, content):
    """Save the executive order as a markdown file without creating backups."""
    # Create directory path using the date
    dir_path = create_markdown_dir(order['date'], "President_Name")  # Replace "President_Name" with actual president's name

    # Create filename from date, EO number, and sanitized title
    date_str = order['date'].strftime('%Y-%m-%d')
    if order.get('eo_number'):
        clean_title = clean_filename(order['title'])
        filename = f"{date_str}-executive-order-{order['eo_number']}-{clean_title}.md"
    else:
        clean_title = clean_filename(order['title'])
        filename = f"{date_str}-{clean_title}.md"

    filepath = os.path.join(dir_path, filename)

    # Format the content
    formatted_content = format_content(content)

    markdown_content = f"""# {order['title']}

## Summary

**Date:** {order['date'].strftime('%B %d, %Y')}

**Document Details:**
- Document Number: {order.get('document_number', 'N/A')}
- Executive Order Number: {order.get('eo_number', 'N/A')}
- Citation: {order.get('citation', 'N/A')}

## Sources
- [Federal Register]({order['link']})
- [XML Source]({order.get('xml_url', '#')})

---

## Executive Order {order.get('eo_number', '')}

{formatted_content}

---

*Filed by the Office of the Federal Register on {order['date'].strftime('%B %d, %Y')}*
"""

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print(f"Saved: {filepath}")
        return True
    except Exception as e:
        print(f"Error saving file: {e}")
        return False

def check_new_orders():
    """Check for new executive orders and process them."""
    print("Starting check for new executive orders...")

    # Calculate the start and end dates for the past 7 days
    today = datetime.now()
    start_date = today - timedelta(days=7)  # 7 days ago
    end_date = today  # Current date and time
    print(f"Fetching orders from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

    # Parameters for the Federal Register API
    params = {
        'conditions[correction]': '0',
        'conditions[presidential_document_type]': 'executive_order',
        'conditions[signing_date][gte]': start_date.strftime('%m/%d/%Y'),
        'conditions[signing_date][lte]': end_date.strftime('%m/%d/%Y'),
        'conditions[type][]': 'PRESDOCU',
        'fields[]': [
            'citation',
            'document_number',
            'end_page',
            'html_url',
            'pdf_url',
            'type',
            'subtype',
            'publication_date',
            'signing_date',
            'start_page',
            'title',
            'disposition_notes',
            'executive_order_number',
            'not_received_for_publication',
            'full_text_xml_url',
            'body_html_url',
            'json_url'
        ],
        'include_pre_1994_docs': 'true',
        'maximum_per_page': 10000,
        'order': 'executive_order',
        'per_page': 10000,
        'format': 'json'
    }

    # Fetch new orders
    results = fetch_all_pages("https://www.federalregister.gov/api/v1/documents", params)
    print(f"Found {len(results)} total orders.")

    # Process each new order
    for result in results:
        try:
            title = result.get('title', '').strip()
            date_str = result.get('signing_date')
            html_url = result.get('html_url')
            xml_url = result.get('full_text_xml_url')
            document_number = result.get('document_number')
            eo_number = result.get('executive_order_number')

            if not all([title, date_str, html_url]):
                print(f"Skipping incomplete order: {title}")
                continue

            date = parser.parse(date_str)

            # Add EO number to title if available
            if eo_number and not title.startswith(f"Executive Order {eo_number}"):
                title = f"Executive Order {eo_number}: {title}"

            order = {
                'title': title,
                'date': date,
                'link': html_url,
                'xml_url': xml_url,
                'document_number': document_number,
                'eo_number': eo_number
            }

            # Check if the file already exists
            dir_path = create_markdown_dir(order['date'], "President_Name")  # Replace "President_Name" with actual president's name
            date_str = order['date'].strftime('%Y-%m-%d')
            clean_title = clean_filename(order['title'])
            if order.get('eo_number'):
                filename = f"{date_str}-executive-order-{order['eo_number']}-{clean_title}.md"
            else:
                filename = f"{date_str}-{clean_title}.md"
            filepath = os.path.join(dir_path, filename)

            if os.path.exists(filepath):
                print(f"Order already exists, skipping: {order['title']} ({order['date']})")
                continue

            # Fetch and save the order content
            print(f"Processing new order: {order['title']} ({order['date']})")
            content = get_order_content(order)
            if content:
                save_as_markdown(order, content)

        except Exception as e:
            print(f"Error processing order: {e}")

    print("Check for new executive orders complete.")

def get_president_by_date(date):
    """Determine the president based on the date of the executive order."""
    presidents = {
        ("2025-01-20", "2029-01-20"): "donald-trump",  # Current term
        ("2021-01-20", "2025-01-20"): "joe-biden",
        ("2017-01-20", "2021-01-20"): "donald-trump",
        ("2009-01-20", "2017-01-20"): "barack-obama",
        ("2001-01-20", "2009-01-20"): "george-w-bush",
        ("1993-01-20", "2001-01-20"): "bill-clinton",
        ("1989-01-20", "1993-01-20"): "george-h-w-bush",
        ("1981-01-20", "1989-01-20"): "ronald-reagan",
        ("1977-01-20", "1981-01-20"): "jimmy-carter",
        ("1974-08-09", "1977-01-20"): "gerald-ford",
        ("1969-01-20", "1974-08-09"): "richard-nixon",
        ("1963-11-22", "1969-01-20"): "lyndon-b-johnson",
        ("1961-01-20", "1963-11-22"): "john-f-kennedy",
        ("1953-01-20", "1961-01-20"): "dwight-d-eisenhower",
        ("1945-04-12", "1953-01-20"): "harry-s-truman",
        ("1933-03-04", "1945-04-12"): "franklin-d-roosevelt",
    }
    
    for (start, end), president in presidents.items():
        start_date = datetime.strptime(start, "%Y-%m-%d")
        end_date = datetime.strptime(end, "%Y-%m-%d")
        if start_date <= date < end_date:
            return president
    
    return "unknown-president"  # Default if no match is found

if __name__ == "__main__":
    check_new_orders()