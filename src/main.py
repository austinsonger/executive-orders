# Updated the main script to integrate all modularized components
from src.api import fetch_all_pages, get_xml_content
from src.utils import create_markdown_dir, clean_filename, get_headers
from src.formatting import format_content

from datetime import datetime, timedelta
from dateutil import parser
import os
import re

LAST_CHECK_FILE = 'last_check.txt'

def save_as_markdown(order, content):
    """Save the executive order as a markdown file without creating backups."""
    # Create directory path using the date
    dir_path = create_markdown_dir(order['date'])

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
    """Check for new executive orders since the last check."""
    print("Starting nightly check for new executive orders...")

    # Retrieve the last check time
    last_check_time = datetime.now() - timedelta(days=1)
    if os.path.exists(LAST_CHECK_FILE):
        with open(LAST_CHECK_FILE, 'r') as f:
            last_check_time = datetime.fromisoformat(f.read().strip())

    print(f"Last check was at: {last_check_time}")

    # Parameters for the Federal Register API
    params = {
        'conditions[correction]': '0',
        'conditions[presidential_document_type]': 'executive_order',
        'conditions[signing_date][gte]': last_check_time.strftime('%m/%d/%Y'),
        'conditions[signing_date][lte]': datetime.now().strftime('%m/%d/%Y'),
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
    print(f"Found {len(results)} new orders.")

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

            print(f"Processing new order: {title} ({date_str})")
            content = get_xml_content(order)

            if content:
                save_as_markdown(order, content)

        except Exception as e:
            print(f"Error processing order: {e}")

    # Update the last check time
    with open(LAST_CHECK_FILE, 'w') as f:
        f.write(datetime.now().isoformat())

    print("Nightly check complete.")

if __name__ == "__main__":
    check_new_orders()