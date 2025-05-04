import os
import sys
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime
from dateutil import parser
import json
import traceback

# Adjust sys.path if run directly
if __name__ == "__main__" and (__package__ is None or __package__ == ''):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    if (parent_dir not in sys.path):
        sys.path.insert(0, parent_dir)
    __package__ = "src"

# Import helpers from the project
try:
    # Try relative imports
    from .utils import create_markdown_dir, clean_filename, save_as_markdown
    print("Using relative imports.")
except (ImportError, SystemError):
    try:
        # Try absolute imports
        from src.utils import create_markdown_dir, clean_filename, save_as_markdown
        print("Using absolute imports from src.")
    except ImportError as e:
        print(f"Error importing modules: {e}")
        print("Please ensure the script is run from the project root directory.")
        sys.exit(1)

# Constants
UCSB_BASE_URL = "https://www.presidency.ucsb.edu"
UCSB_SEARCH_URL = f"{UCSB_BASE_URL}/advanced-search"

def get_headers():
    """Get headers to mimic a browser request"""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': UCSB_BASE_URL,
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    }

# --- Added: Configure requests session with retries ---
def create_session_with_retries(retries=3, backoff_factor=0.5, status_forcelist=(500, 502, 503, 504), timeout=60):
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.headers.update(get_headers()) # Add default headers to the session
    session.request_timeout = timeout # Default timeout for requests made with this session
    return session

# Global session object
REQUESTS_SESSION = create_session_with_retries()
# --- End Added ---

# Presidents dictionary mapping UCSB person IDs to your folder structure slugs
# The person ID is used in the search URL - UPDATED with correct person IDs from the URLs

PRESIDENTS_UCSB = {
    # Format: "your-slug": ("UCSB person ID", "start_date", "end_date", "display_name")
    "ronald-reagan": ("200296", "1981-01-20", "1989-01-20", "Ronald Reagan"),
    "jimmy-carter": ("200295", "1977-01-20", "1981-01-20", "Jimmy Carter"),
    "gerald-r-ford": ("200294", "1974-08-09", "1977-01-20", "Gerald R. Ford"),
    "richard-nixon": ("200293", "1969-01-20", "1974-08-09", "Richard Nixon"),
    "lyndon-b-johnson": ("200292", "1963-11-22", "1969-01-20", "Lyndon B. Johnson"),
    "john-f-kennedy": ("200291", "1961-01-20", "1963-11-22", "John F. Kennedy"),
    "dwight-d-eisenhower": ("200290", "1953-01-20", "1961-01-20", "Dwight D. Eisenhower"),
    "harry-s-truman": ("200289", "1945-04-12", "1953-01-20", "Harry S. Truman"),
    "franklin-d-roosevelt": ("200288", "1933-03-04", "1945-04-12", "Franklin D. Roosevelt"),
    "herbert-hoover": ("200287", "1929-03-04", "1933-03-04", "Herbert Hoover"),
    "calvin-coolidge": ("200286", "1923-08-02", "1929-03-04", "Calvin Coolidge"),
    "warren-g-harding": ("200285", "1921-03-04", "1923-08-02", "Warren G. Harding"),
    "woodrow-wilson": ("200284", "1913-03-04", "1921-03-04", "Woodrow Wilson"),
    "william-h-taft": ("200283", "1909-03-04", "1913-03-04", "William H. Taft"),
    "theodore-roosevelt": ("200282", "1901-09-14", "1909-03-04", "Theodore Roosevelt"),
    "william-mckinley": ("200281", "1897-03-04", "1901-09-14", "William McKinley"),
    "grover-cleveland-2": ("200280", "1893-03-04", "1897-03-04", "Grover Cleveland (2nd term)"),
    "benjamin-harrison": ("200279", "1889-03-04", "1893-03-04", "Benjamin Harrison"),
    "grover-cleveland-1": ("200278", "1885-03-04", "1889-03-04", "Grover Cleveland (1st term)"),
    "chester-a-arthur": ("200277", "1881-09-19", "1885-03-04", "Chester A. Arthur"),
    "james-a-garfield": ("200276", "1881-03-04", "1881-09-19", "James A. Garfield"),
    "rutherford-b-hayes": ("200275", "1877-03-04", "1881-03-04", "Rutherford B. Hayes"),
    "ulysses-s-grant": ("200274", "1869-03-04", "1877-03-04", "Ulysses S. Grant"),
    "andrew-johnson": ("200273", "1865-04-15", "1869-03-04", "Andrew Johnson"),
    "abraham-lincoln": ("200272", "1861-03-04", "1865-04-15", "Abraham Lincoln"),
    "james-buchanan": ("200271", "1857-03-04", "1861-03-04", "James Buchanan"),
    "franklin-pierce": ("200270", "1853-03-04", "1857-03-04", "Franklin Pierce"),
    "millard-fillmore": ("200269", "1850-07-09", "1853-03-04", "Millard Fillmore"),
    "zachary-taylor": ("200268", "1849-03-04", "1850-07-09", "Zachary Taylor"),
    "james-k-polk": ("200267", "1845-03-04", "1849-03-04", "James K. Polk"),
    "john-tyler": ("200266", "1841-04-04", "1845-03-04", "John Tyler"),
    "william-h-harrison": ("200265", "1841-03-04", "1841-04-04", "William Henry Harrison"),
    "martin-van-buren": ("200264", "1837-03-04", "1841-03-04", "Martin Van Buren"),
    "andrew-jackson": ("200263", "1829-03-04", "1837-03-04", "Andrew Jackson"),
    "john-quincy-adams": ("200262", "1825-03-04", "1829-03-04", "John Quincy Adams"),
    "james-monroe": ("200261", "1817-03-04", "1825-03-04", "James Monroe"),
    "james-madison": ("200260", "1809-03-04", "1817-03-04", "James Madison"),
    "thomas-jefferson": ("200259", "1801-03-04", "1809-03-04", "Thomas Jefferson"),
    "john-adams": ("200258", "1797-03-04", "1801-03-04", "John Adams"),
    "george-washington": ("200257", "1789-04-30", "1797-03-04", "George Washington"),
}




def fetch_orders_for_page(president_slug, person_id, page=0):
    """
    Fetch a page of executive orders for a specific president from the UCSB Presidency Project.
    
    Args:
        president_slug: The slug used in your file structure
        person_id: The UCSB person ID for the president 
        page: Page number to fetch (0-based for UCSB)
        
    Returns:
        List of orders found on the page
    """
    orders = []
    
    # Build the search URL with correct parameters based on the provided URLs
    # Only include page parameter if it's not the first page (page > 0)
    url = f"{UCSB_SEARCH_URL}?field-keywords=&field-keywords2=&field-keywords3=&from%5Bdate%5D=&to%5Bdate%5D=&person2={person_id}&category2%5B%5D=58&items_per_page=100"
    
    # Add page parameter only if not the first page
    if page > 0:
        url += f"&page={page}"
    
    try:
        print(f"Fetching page {page+1} for {president_slug}...")
        print(f"Using URL: {url}")
        
        # --- Modified: Use session with timeout ---
        response = REQUESTS_SESSION.get(url, timeout=REQUESTS_SESSION.request_timeout)
        # --- End Modified ---
        response.raise_for_status()
        
        # Save HTML for debugging if needed
        debug_file = os.path.join("debug", f"ucsb_debug_{president_slug}_page{page}.html")
        with open(debug_file, "w", encoding="utf-8") as f:
            f.write(response.text)
        print(f"HTML content saved to {debug_file} for debugging")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Debug: Print the title to make sure we're getting a search results page
        page_title = soup.title.text if soup.title else 'No title'
        print(f"Page title: {page_title}")
        
        # Look for the results table - UCSB uses a table to display executive orders
        # This is specific to the table format seen in the debug HTML
        results_table = soup.select_one('table.views-table')
        
        if not results_table:
            print("No results table found on this page.")
            return []
        
        # Get all rows from the table body
        rows = results_table.select('tbody tr')
        
        if not rows:
            print("No result rows found in the table.")
            return []
        
        print(f"Found {len(rows)} results on page {page+1}")
        
        for row in rows:
            try:
                # Extract cells from the row - should have date, person, and title
                cells = row.select('td')
                
                if len(cells) < 3:
                    print(f"  - Skipping row with insufficient cells: {len(cells)}")
                    continue
                
                # Extract date from the first cell
                date_cell = cells[0]
                date_text = date_cell.get_text(strip=True)
                try:
                    date_obj = parser.parse(date_text)
                except Exception as e:
                    print(f"  - Error parsing date '{date_text}': {e}")
                    continue
                
                # Extract title and link from the third cell
                title_cell = cells[2]
                title_link = title_cell.select_one('a')
                
                if not title_link:
                    print("  - No title link found in row")
                    continue
                
                title = title_link.get_text(strip=True)
                detail_url = title_link['href']
                
                if not detail_url.startswith('http'):
                    detail_url = f"{UCSB_BASE_URL}{detail_url}"
                
                # Extract EO number from title
                eo_number = None
                eo_match = re.search(r'Executive Order (?:Number )?(\d+)', title, re.IGNORECASE)
                if eo_match:
                    eo_number = eo_match.group(1)
                else:
                    # Try alternate formats
                    alternate_patterns = [
                        r'(?:EO|E\.O\.) (?:Number )?(\d+)',
                        r'Order (?:No\.|Number) (\d+)',
                        r'(?:No\.|Number) (\d+)'
                    ]
                    
                    for pattern in alternate_patterns:
                        eo_match = re.search(pattern, title, re.IGNORECASE)
                        if (eo_match):
                            eo_number = eo_match.group(1)
                            break
                
                order = {
                    'title': title,
                    'date': date_obj,
                    'link': detail_url,
                    'eo_number': eo_number
                }
                
                print(f"  - Found order: {title} ({date_obj.strftime('%Y-%m-%d')})")
                orders.append(order)
                
            except Exception as e:
                print(f"  - Error processing row: {e}")
                traceback.print_exc()
                continue
        
        return orders
    
    except Exception as e:
        print(f"Error fetching search page {page+1}: {e}")
        traceback.print_exc()
        return []

def get_order_content_ucsb(detail_url):
    """
    Fetches and extracts the content of an executive order from its detail page.
    
    Args:
        detail_url: URL to the detail page of the executive order
        
    Returns:
        String content of the executive order or None if failed
    """
    try:
        print(f"  - Fetching content from: {detail_url}")
        # --- Modified: Use session with timeout ---
        response = REQUESTS_SESSION.get(detail_url, timeout=REQUESTS_SESSION.request_timeout)
        # --- End Modified ---
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Primary content container in UCSB pages is usually 'div.field-docs-content'
        # or variations of it like 'div.field--name-field-docs-content'
        content_div = None
        
        # Try specific selectors that match the UCSB site structure
        selectors = [
            'div.field-docs-content',
            'div.field--name-field-docs-content',
            'div.node__content div.clearfix',
            'div.field-body',
            'div.body',
            'div.node__content',
            'article .content',
            'div#document-content',  # Fallback to potential Federal Register style
            'article'
        ]
        
        for selector in selectors:
            content_div = soup.select_one(selector)
            if content_div:
                print(f"  - Found content using selector: '{selector}'")
                break
        
        if not content_div:
            print("  - Could not find content section with known selectors")
            # Last resort: try to find any div with substantial text
            text_divs = []
            for div in soup.find_all('div'):
                text = div.get_text(strip=True)
                if len(text) > 500:  # Only consider divs with substantial text
                    text_divs.append((div, len(text)))
            
            if text_divs:
                # Sort by text length, largest first
                text_divs.sort(key=lambda x: x[1], reverse=True)
                content_div = text_divs[0][0]
                print(f"  - Found content using largest text div (size: {text_divs[0][1]} chars)")
        
        if not content_div:
            print("  - Could not find content section")
            return None
        
        # Try to extract structured content like paragraphs and headers
        # This keeps the document structure better than just getting all text
        paragraphs = content_div.find_all(['p', 'h2', 'h3', 'h4', 'h5', 'blockquote'])
        
        if paragraphs:
            # Join paragraphs with double newlines to preserve structure
            content = "\n\n".join(p.get_text().strip() for p in paragraphs)
        else:
            # Fallback to getting all text if paragraphs not found
            content = content_div.get_text(separator='\n\n', strip=True)
        
        # Clean up the content
        content = re.sub(r'\n{3,}', '\n\n', content)  # Remove excess newlines
        content = re.sub(r'^\s+', '', content, flags=re.MULTILINE)  # Remove leading whitespace
        
        # Add special formatting for signature block often found in executive orders
        signature_match = re.search(r'([A-Z][a-z]+\s+[A-Z]\.\s+[A-Z][a-z]+|[A-Z][a-z]+\s+[A-Z][a-z]+)\s*[,.]?\s*(THE WHITE HOUSE|The White House)[,.]?\s*([\w\s,]+\d{1,2},\s*\d{4}|[\w\s,]+\d{4})', content)
        if signature_match:
            signature_part = signature_match.group(0)
            # Format the signature part with proper spacing
            formatted_signature = f"\n\n{signature_part}"
            content = content.replace(signature_part, formatted_signature)
        
        return content.strip()
        
    except Exception as e:
        print(f"  - Error fetching order content: {e}")
        # Don't print full traceback here for timeouts/retries, just the error
        if not isinstance(e, (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError)):
             traceback.print_exc()
        return None

def fetch_all_orders_for_president(president_slug):
    """
    Fetches all executive orders for a specific president from UCSB.
    
    Args:
        president_slug: The slug for the president in your file structure
        
    Returns:
        Tuple of (processed_count, skipped_count, error_count)
    """
    if president_slug not in PRESIDENTS_UCSB:
        print(f"Error: President slug '{president_slug}' not found in PRESIDENTS_UCSB dictionary")
        return (0, 0, 0)
    
    person_id, start_date, end_date, display_name = PRESIDENTS_UCSB[president_slug]
    
    print(f"\n--- Starting fetch for {display_name} (using UCSB person ID: {person_id}) ---")
    
    all_orders = []
    page = 0
    pages_fetched = 0
    
    # Initialize counts here to fix scope issues
    processed_count = 0
    skipped_count = 0
    error_count = 0
    
    # Fetch all pages of results
    while True:
        orders = fetch_orders_for_page(president_slug, person_id, page)
        if not orders:
            break
            
        all_orders.extend(orders)
        page += 1
        pages_fetched = page
        
        # Be polite to the server
        time.sleep(2)
    
    print(f"Found {len(all_orders)} total orders across {pages_fetched} pages for {display_name}")
    
    # Process each order
    for order in all_orders:
        try:
            # Prepare order data
            title = order['title']
            date_obj = order['date']
            link = order['link']  # Get the link from the order dictionary
            eo_number = order.get('eo_number')
            
            # Create standard metadata object
            order_data = {
                'title': title,
                'date': date_obj,
                'link': link,
                'eo_number': eo_number,
                # Add other fields to match your expected structure
                'document_number': None,
                'pdf_url': None,
                'xml_url': None,
                'publication_date': date_obj.strftime('%Y-%m-%d'),
                'citation': None
            }
            
            # Create directory path
            dir_path = create_markdown_dir(order_data['date'], president_slug)
            file_date_str = order_data['date'].strftime('%Y-%m-%d')
            clean_title_part = clean_filename(order_data['title'])
            
            # Create filename
            if order_data.get('eo_number'):
                filename = f"{file_date_str}-executive-order-{order_data['eo_number']}-{clean_title_part}.md"
            else:
                eo_match = re.match(r'executive order (\d+)', order_data['title'], re.IGNORECASE)
                if eo_match:
                    filename = f"{file_date_str}-executive-order-{eo_match.group(1)}-{clean_title_part}.md"
                else:
                    filename = f"{file_date_str}-{clean_title_part}.md"
                
            filepath = os.path.join(dir_path, filename)
            
            # Skip if file exists
            if os.path.exists(filepath):
                print(f"  - Skipping (already exists): {filepath}")
                skipped_count += 1
                continue
                
            print(f"Processing: {filepath}")
            
            # Get content
            content = get_order_content_ucsb(order_data['link'])
            
            if content:
                # Save content as markdown
                if save_as_markdown(order_data, content):
                    processed_count += 1
                    print(f"  - Saved: {filepath}")
                else:
                    print(f"  - Error: Failed to save {filepath}")
                    error_count += 1
            else:
                print(f"  - Error: Failed to retrieve content for {title}")
                error_count += 1
            
            # Be polite to the server
            time.sleep(1)
            
        except Exception as e:
            print(f"Error processing order '{order.get('title', 'Unknown')}': {e}")
            traceback.print_exc()
            error_count += 1
    
    print(f"--- Finished fetch for {display_name} ---")
    print(f"Summary: Processed={processed_count}, Skipped={skipped_count}, Errors={error_count}")
    return (processed_count, skipped_count, error_count)
            
def main():
    """Main function to run when script is executed directly"""
    print("Starting UCSB Presidency Project fetch for historical presidents...")
    
    total_processed = 0
    total_skipped = 0
    total_errors = 0
    
    # Get command line args if specific presidents provided
    target_presidents = sys.argv[1:] if len(sys.argv) > 1 else list(PRESIDENTS_UCSB.keys())
    
    for president in target_presidents:
        if president not in PRESIDENTS_UCSB:
            print(f"Warning: '{president}' is not a valid president slug. Skipping.")
            continue
            
        processed, skipped, errors = fetch_all_orders_for_president(president)
        total_processed += processed
        total_skipped += skipped
        total_errors += errors
        
        # Pause before next president
        if president != target_presidents[-1]:
            print("\nPausing for 5 seconds before fetching next president...")
            time.sleep(5)
    
    print("\n" + "=" * 50)
    print("UCSB Presidency Project Fetch Complete!")
    print(f"Total Processed: {total_processed}")
    print(f"Total Skipped: {total_skipped}")
    print(f"Total Errors: {total_errors}")
    print("=" * 50)

if __name__ == "__main__":
    main()