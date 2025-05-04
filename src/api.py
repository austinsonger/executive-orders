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

def get_order_content(order):
    """Get the content of an executive order, prioritizing XML, fallback to HTML."""
    # Try XML first
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
            print(f"Error fetching XML content via get_order_content: {e}")
            # Fall through to HTML fallback

    # If XML fails or is not available, try HTML
    print("XML failed or not available. Trying HTML fallback.")
    if order.get('link'): # 'link' should be the html_url
        try:
            html_content = get_html_content(order['link'])
            if html_content:
                return html_content
            else:
                 print("HTML fallback failed to retrieve content.")
        except Exception as e:
            print(f"Error during HTML fallback: {e}")

    print(f"Could not retrieve content from XML or HTML for {order.get('title')}")
    return None

# Note: scrape_historical_orders was in the original file but not used by check_new_orders.
# It can be added here if needed for other purposes.