import requests
import time
from bs4 import BeautifulSoup
from .utils import get_headers

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