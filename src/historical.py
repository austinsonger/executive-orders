import os
import sys
from datetime import datetime, timedelta
from dateutil import parser
import re
import traceback
import time
import requests # <-- Add requests import
from bs4 import BeautifulSoup # <-- Add BeautifulSoup import

# Assuming src is in PYTHONPATH or running with python -m src.historical
try:
    # Import only necessary functions from other modules
    from .api import fetch_all_pages, get_xml_content, get_headers
    from .utils import create_markdown_dir, clean_filename, save_as_markdown
except ImportError:
    # Allow running directly if src is added to path externally
    from api import fetch_all_pages, get_xml_content, get_headers
    from utils import create_markdown_dir, clean_filename, save_as_markdown

FEDERAL_REGISTER_API_URL = "https://www.federalregister.gov/api/v1/documents"

# Define presidents and their slugs (matching API slugs)
PRESIDENTS_TO_FETCH = {
    "william-j-clinton": ("1993-01-20", "2001-01-20"),
    "george-h-w-bush": ("1989-01-20", "1993-01-20"),
    "ronald-reagan": ("1981-01-20", "1989-01-20"),
    "jimmy-carter": ("1977-01-20", "1981-01-20"),
    "gerald-r-ford": ("1974-08-09", "1977-01-20"),
    "richard-nixon": ("1969-01-20", "1974-08-09"),
    "lyndon-b-johnson": ("1963-11-22", "1969-01-20"),
    "john-f-kennedy": ("1961-01-20", "1963-11-22"),
    "dwight-d-eisenhower": ("1953-01-20", "1961-01-20"),
    "harry-s-truman": ("1945-04-12", "1953-01-20"),
    "franklin-d-roosevelt": ("1933-03-04", "1945-04-12"),
}

# --- Local Helper Functions (Copied/Adapted to keep changes in this file) ---

def get_president_by_date_historical(date):
    """Determine the president based on the date - uses API-consistent slugs."""
    if isinstance(date, str):
        date = parser.parse(date)

    # Use slugs consistent with Federal Register API
    presidents = {
        ("2021-01-20", "2025-01-20"): "joseph-r-biden",
        ("2017-01-20", "2021-01-20"): "donald-trump",
        ("2009-01-20", "2017-01-20"): "barack-obama",
        ("2001-01-20", "2009-01-20"): "george-w-bush",
        ("1993-01-20", "2001-01-20"): "william-j-clinton",
        ("1989-01-20", "1993-01-20"): "george-h-w-bush",
        ("1981-01-20", "1989-01-20"): "ronald-reagan",
        ("1977-01-20", "1981-01-20"): "jimmy-carter",
        ("1974-08-09", "1977-01-20"): "gerald-r-ford",
        ("1969-01-20", "1974-08-09"): "richard-nixon",
        ("1963-11-22", "1969-01-20"): "lyndon-b-johnson",
        ("1961-01-20", "1963-11-22"): "john-f-kennedy",
        ("1953-01-20", "1961-01-20"): "dwight-d-eisenhower",
        ("1945-04-12", "1953-01-20"): "harry-s-truman",
        ("1933-03-04", "1945-04-12"): "franklin-d-roosevelt",
    }

    for (start, end), president in presidents.items():
        start_date = datetime.strptime(start, "%Y-%m-%d")
        if date.tzinfo:
            start_date = start_date.replace(tzinfo=date.tzinfo)
            end_date = datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=date.tzinfo)
        else:
            end_date = datetime.strptime(end, "%Y-%m-%d")
        if start_date <= date < end_date:
            return president
    return "unknown-president"

def get_html_content_historical(html_url):
    """Fetch and parse HTML content from the Federal Register document page (local version)."""
    try:
        print(f"  - Attempting HTML fallback from: {html_url}")
        # Uses get_headers imported from api module
        response = requests.get(html_url, headers=get_headers(), timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        content_div = soup.find('div', id='document-content')
        if not content_div:
            content_div = soup.find('article')
            if not content_div:
                 content_div = soup.find('div', class_='article-content')
        if not content_div:
            print("  - HTML Fallback: Could not find main content container.")
            return None
        full_content = content_div.get_text(separator='\n\n', strip=True)
        full_content = re.sub(r'\n\s*\n', '\n\n', full_content)
        full_content = re.sub(r'^\s+', '', full_content, flags=re.MULTILINE)
        print("  - HTML Fallback successful.")
        return full_content.strip()
    except Exception as e:
        print(f"  - Error fetching/parsing HTML content: {str(e)}")
        return None

def get_order_content_historical(order):
    """Get order content, prioritizing XML, fallback to HTML (local version)."""
    # Try XML first (uses get_xml_content imported from api module)
    if order.get('xml_url'):
        try:
            print(f"Fetching XML content from: {order['xml_url']}")
            content = get_xml_content(order['xml_url'])
            if content:
                print("XML content fetched successfully.")
                return content
            else:
                print("XML content fetch returned None.")
        except Exception as e:
            print(f"Error fetching XML content: {e}")
            # Fall through

    # Fallback to HTML
    print("XML failed or not available. Trying HTML fallback.")
    if order.get('link'):
        try:
            # Uses local get_html_content_historical
            html_content = get_html_content_historical(order['link'])
            if html_content:
                return html_content
            else:
                 print("HTML fallback failed to retrieve content.")
        except Exception as e:
            print(f"Error during HTML fallback: {e}")

    print(f"Could not retrieve content from XML or HTML for {order.get('title')}")
    return None

# --- Main Fetching Logic ---

def fetch_orders_for_president(president_slug, start_date_str, end_date_str):
    """Fetches and saves executive orders for a specific president using the president slug."""
    # ... (display name logic remains the same) ...
    president_name_display = president_slug.replace('-', ' ').title()
    if president_slug == "george-h-w-bush":
        president_name_display = "George H.W. Bush"
    elif president_slug == "gerald-r-ford":
         president_name_display = "Gerald R. Ford"

    print(f"\n--- Starting fetch for {president_name_display} (using president slug: {president_slug}) ---")

    params = {
        'conditions[correction]': '0',
        'conditions[president]': president_slug,
        'conditions[presidential_document_type]': 'executive_order',
        'conditions[type][]': 'PRESDOCU',
        'fields[]': [
            'citation', 'document_number', 'end_page', 'html_url', 'pdf_url',
            'type', 'subtype', 'publication_date', 'signing_date', 'start_page',
            'title', 'disposition_notes', 'executive_order_number',
            'not_received_for_publication', 'full_text_xml_url', 'body_html_url',
            'json_url'
        ],
        'include_pre_1994_docs': 'true',
        'per_page': 1000,
        'order': 'signing_date',
        'format': 'json'
    }

    results = fetch_all_pages(FEDERAL_REGISTER_API_URL, params)
    print(f"Found {len(results)} total orders for {president_name_display}.")

    processed_count = 0
    skipped_count = 0
    error_count = 0

    for result in results:
        try:
            # ... (data extraction remains the same) ...
            title = result.get('title', '').strip()
            date_str = result.get('signing_date')
            html_url = result.get('html_url')
            xml_url = result.get('full_text_xml_url')
            pdf_url = result.get('pdf_url')
            document_number = result.get('document_number')
            eo_number = result.get('executive_order_number')
            citation = result.get('citation')
            publication_date = result.get('publication_date')

            if not all([title, date_str, html_url]):
                skipped_count += 1
                continue

            date = parser.parse(date_str)
            # Use the local version for the warning check
            calculated_president = get_president_by_date_historical(date)
            if calculated_president != president_slug and calculated_president != "unknown-president":
                 print(f"  - Warning: Order date {date_str} ({title}) calculates to president '{calculated_president}', expected '{president_slug}'. Saving under '{president_slug}'.")

            if eo_number and not re.match(rf'Executive Order {eo_number}', title, re.IGNORECASE):
                 title = f"Executive Order {eo_number}: {title}"

            order_data = {
                'title': title, 'date': date, 'link': html_url, 'xml_url': xml_url,
                'pdf_url': pdf_url, 'document_number': document_number, 'eo_number': eo_number,
                'citation': citation, 'publication_date': publication_date
            }

            # --- File Exists Check --- (uses imported create_markdown_dir, clean_filename)
            dir_path = create_markdown_dir(order_data['date'], president_slug)
            file_date_str = order_data['date'].strftime('%Y-%m-%d')
            clean_title_part = clean_filename(order_data['title'])
            filename = ""
            if order_data.get('eo_number'):
                 filename = f"{file_date_str}-executive-order-{order_data['eo_number']}-{clean_title_part}.md"
            else:
                 eo_match = re.match(r'executive order (\d+)', order_data['title'], re.IGNORECASE)
                 if eo_match:
                     filename = f"{file_date_str}-executive-order-{eo_match.group(1)}-{clean_title_part}.md"
                 else:
                     filename = f"{file_date_str}-{clean_title_part}.md"
            filepath = os.path.join(dir_path, filename)
            if os.path.exists(filepath):
                skipped_count += 1
                continue
            # --- End File Exists Check ---

            print(f"Processing: {filepath}")
            # Use the local content fetching function with fallback
            content = get_order_content_historical(order_data)

            if content:
                # Uses imported save_as_markdown
                if save_as_markdown(order_data, content):
                    processed_count += 1
                else:
                    print(f"Failed to save: {filepath}")
                    error_count += 1
            else:
                print(f"  - ERROR: Failed to retrieve content for {order_data['title']} from both XML and HTML.")
                error_count += 1

            time.sleep(0.1)

        except Exception as e:
            print(f"Error processing result {result.get('document_number', 'N/A')}: {e}")
            # traceback.print_exc()
            error_count += 1

    # ... (summary print remains the same) ...
    print(f"--- Finished fetch for {president_name_display} ---")
    print(f"Summary: Processed={processed_count}, Skipped (already exists)={skipped_count}, Errors={error_count}")
    return processed_count, skipped_count, error_count

# ... (main execution block remains the same) ...
if __name__ == '__main__':
    total_processed = 0
    total_skipped = 0
    total_errors = 0

    print("Starting historical fetch for Presidents using president slugs...")

    for president, (start_date, end_date) in PRESIDENTS_TO_FETCH.items():
        processed, skipped, errors = fetch_orders_for_president(president, start_date, end_date)
        total_processed += processed
        total_skipped += skipped
        total_errors += errors
        print("Pausing for 5 seconds before next president...")
        time.sleep(5)

    print("\n" + "=" * 40)
    print("Overall Historical Fetch Complete.")
    print(f"Total Processed: {total_processed}")
    print(f"Total Skipped: {total_skipped}")
    print(f"Total Errors: {total_errors}")
    print("=" * 40)
