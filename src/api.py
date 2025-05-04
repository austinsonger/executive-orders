import requests
from bs4 import BeautifulSoup
import time
import re

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

def get_html_content(html_url):
    """Fetch and parse HTML content from the Federal Register document page."""
    try:
        print(f"  - Attempting HTML fallback from: {html_url}")
        response = requests.get(html_url, headers=get_headers(), timeout=30)

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

def get_order_content(order):
    """Get the content of an executive order, prioritizing XML if available."""
    if order.get('xml_url'):
        try:
            print(f"Fetching XML content from: {order['xml_url']}")
            # Use get_xml_content function defined above
            content = get_xml_content(order['xml_url'])
            if content:
                return content

        except Exception as e:
            print(f"Error fetching XML content via get_order_content: {e}")
            # Fall through to return None if XML fails

    print("No XML URL provided or failed to fetch XML content.")
    return None

# Note: scrape_historical_orders was in the original file but not used by check_new_orders.
# It can be added here if needed for other purposes.