import os
from datetime import datetime, timedelta
from dateutil import parser
import sys
import re # <-- Added import

# Import functions from sibling modules
from .api import fetch_all_pages, get_order_content
from .utils import create_markdown_dir, clean_filename, save_as_markdown, get_president_by_date

# Constants (if any specific to main logic)
FEDERAL_REGISTER_API_URL = "https://www.federalregister.gov/api/v1/documents"
CHECK_PERIOD_DAYS = 7 # How many days back to check for new orders

def check_new_orders():
    """Check for new executive orders and process them."""
    print("Starting check for new executive orders...")

    # Calculate the start and end dates for the check period
    today = datetime.now()
    start_date = today - timedelta(days=CHECK_PERIOD_DAYS)
    end_date = today
    print(f"Fetching orders signed between {start_date.strftime('%Y-%m-%d')} and {end_date.strftime('%Y-%m-%d')}")

    # Parameters for the Federal Register API
    params = {
        'conditions[correction]': '0',
        'conditions[presidential_document_type]': 'executive_order',
        'conditions[signing_date][gte]': start_date.strftime('%m/%d/%Y'),
        'conditions[signing_date][lte]': end_date.strftime('%m/%d/%Y'),
        'conditions[type][]': 'PRESDOCU',
        'fields[]': [
            'citation', 'document_number', 'end_page', 'html_url', 'pdf_url',
            'type', 'subtype', 'publication_date', 'signing_date', 'start_page',
            'title', 'disposition_notes', 'executive_order_number',
            'not_received_for_publication', 'full_text_xml_url', 'body_html_url',
            'json_url'
        ],
        'per_page': 1000, # Adjust as needed, fetch_all_pages handles pagination
        'order': 'signing_date', # Order by signing date
        'format': 'json'
    }

    # Fetch new orders using the API module function
    results = fetch_all_pages(FEDERAL_REGISTER_API_URL, params)
    print(f"Found {len(results)} potential new orders in the date range.")

    processed_count = 0
    skipped_count = 0
    error_count = 0

    # Process each result
    for result in results:
        try:
            title = result.get('title', '').strip()
            date_str = result.get('signing_date')
            html_url = result.get('html_url')
            xml_url = result.get('full_text_xml_url')
            pdf_url = result.get('pdf_url') # Get PDF URL too
            document_number = result.get('document_number')
            eo_number = result.get('executive_order_number')
            citation = result.get('citation')
            publication_date = result.get('publication_date') # Get publication date

            # Basic validation
            if not all([title, date_str, html_url]):
                print(f"Skipping incomplete order data: Title='{title}', Date='{date_str}', URL='{html_url}'")
                skipped_count += 1
                continue

            date = parser.parse(date_str)
            president_name = get_president_by_date(date)

            # Add EO number to title if available and not already present
            if eo_number and not re.match(rf'Executive Order {eo_number}', title, re.IGNORECASE):
                 title = f"Executive Order {eo_number}: {title}"


            order_data = {
                'title': title,
                'date': date,
                'link': html_url,
                'xml_url': xml_url,
                'pdf_url': pdf_url,
                'document_number': document_number,
                'eo_number': eo_number,
                'citation': citation,
                'publication_date': publication_date
            }

            # --- Check if the file already exists ---
            dir_path = create_markdown_dir(order_data['date'], president_name)
            file_date_str = order_data['date'].strftime('%Y-%m-%d')
            clean_title_part = clean_filename(order_data['title'])

            if order_data.get('eo_number'):
                 filename = f"{file_date_str}-executive-order-{order_data['eo_number']}-{clean_title_part}.md"
            else:
                 # Handle cases where EO number might be missing but title implies it
                 eo_match = re.match(r'executive order (\d+)', order_data['title'], re.IGNORECASE)
                 if eo_match:
                     filename = f"{file_date_str}-executive-order-{eo_match.group(1)}-{clean_title_part}.md"
                 else:
                     filename = f"{file_date_str}-{clean_title_part}.md"

            filepath = os.path.join(dir_path, filename)

            if os.path.exists(filepath):
                # print(f"Order already exists, skipping: {order_data['title']} ({order_data['date'].strftime('%Y-%m-%d')})")
                skipped_count += 1
                continue
            # --- End File Exists Check ---

            # Fetch and save the order content
            print(f"Processing new order: {order_data['title']} ({order_data['date'].strftime('%Y-%m-%d')})")
            content = get_order_content(order_data) # Use API module function
            if content:
                if save_as_markdown(order_data, content): # Use Utils module function
                    processed_count += 1
                else:
                    error_count += 1 # Increment error count if save failed
            else:
                print(f"Could not retrieve content for: {order_data['title']}")
                error_count += 1 # Increment error count if content retrieval failed


        except Exception as e:
            print(f"Error processing result: {result.get('document_number', 'N/A')} - {e}")
            error_count += 1
            # Optionally add more detailed error logging here
            import traceback
            traceback.print_exc()


    print("-" * 20)
    print("Check for new executive orders complete.")
    print(f"Summary: Processed={processed_count}, Skipped (already exists)={skipped_count}, Errors={error_count}")
    print("-" * 20)


# Main execution block
if __name__ == "__main__":
    # This allows running the check directly via `python -m src.main`
    check_new_orders()