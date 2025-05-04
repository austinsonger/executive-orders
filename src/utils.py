import os
import re
from datetime import datetime
from .formatting import format_content # Import from sibling module

def create_markdown_dir(date, president_name):
    """Create directory for the president, year, and month if they don't exist"""
    base_dir = "Presidential_Executive_Orders"  # Base directory
    president_dir = os.path.join(base_dir, president_name)  # Directory for the president
    year = date.year
    month = date.strftime('%m-%B')  # e.g., "01-January"
    year_dir = os.path.join(president_dir, str(year))
    month_dir = os.path.join(year_dir, month)

    # Use os.makedirs with exist_ok=True to simplify directory creation
    os.makedirs(month_dir, exist_ok=True)
    return month_dir

def clean_filename(title):
    """Convert title to valid filename"""
    # Remove EO number prefix if present, as it's added separately
    title = re.sub(r'^Executive Order \d+: ', '', title, flags=re.IGNORECASE)
    # Sanitize
    filename = re.sub(r'[^\\w\\s-]', '', title).strip().lower()
    # Replace spaces with hyphens
    filename = re.sub(r'\\s+', '-', filename)
    # Limit length (optional, but good practice)
    max_len = 100
    if len(filename) > max_len:
        filename = filename[:max_len].rsplit('-', 1)[0] # Cut at last hyphen
    return filename


def get_president_by_date(date):
    """Determine the president based on the date of the executive order."""
    # Ensure date is a datetime object
    if isinstance(date, str):
        from dateutil import parser
        date = parser.parse(date)

    # Use slugs consistent with Federal Register API
    presidents = {
        # ("2025-01-20", "2029-01-20"): "donald-trump", # Future/Current - adjust as needed
        ("2021-01-20", "2025-01-20"): "joseph-r-biden", # API uses joseph-r-biden
        ("2017-01-20", "2021-01-20"): "donald-trump",
        ("2009-01-20", "2017-01-20"): "barack-obama",
        ("2001-01-20", "2009-01-20"): "george-w-bush",
        ("1993-01-20", "2001-01-20"): "william-j-clinton", # API uses william-j-clinton
        ("1989-01-20", "1993-01-20"): "george-h-w-bush",
        ("1981-01-20", "1989-01-20"): "ronald-reagan",
        ("1977-01-20", "1981-01-20"): "jimmy-carter",
        ("1974-08-09", "1977-01-20"): "gerald-r-ford", # API uses gerald-r-ford
        ("1969-01-20", "1974-08-09"): "richard-nixon",
        ("1963-11-22", "1969-01-20"): "lyndon-b-johnson",
        ("1961-01-20", "1963-11-22"): "john-f-kennedy",
        ("1953-01-20", "1961-01-20"): "dwight-d-eisenhower",
        ("1945-04-12", "1953-01-20"): "harry-s-truman",
        ("1933-03-04", "1945-04-12"): "franklin-d-roosevelt",
    }

    for (start, end), president in presidents.items():
        start_date = datetime.strptime(start, "%Y-%m-%d")
        # Handle potential time zone issues if date has timezone info
        if date.tzinfo:
            start_date = start_date.replace(tzinfo=date.tzinfo)
            end_date = datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=date.tzinfo)
        else:
             end_date = datetime.strptime(end, "%Y-%m-%d")

        if start_date <= date < end_date:
            return president

    return "unknown-president"  # Default if no match is found


def save_as_markdown(order, content):
    """Save the executive order as a markdown file without creating backups."""
    if not content:
        print(f"Skipping save for {order['title']} due to empty content.")
        return False

    president_name = get_president_by_date(order['date'])
    if president_name == "unknown-president":
        print(f"Warning: Could not determine president for date {order['date']}. Saving to 'unknown-president' directory.")

    # Create directory path using the date and president name
    dir_path = create_markdown_dir(order['date'], president_name)

    # Create filename from date, EO number, and sanitized title
    date_str = order['date'].strftime('%Y-%m-%d')
    clean_title_part = clean_filename(order['title'])

    if order.get('eo_number'):
        filename = f"{date_str}-executive-order-{order['eo_number']}-{clean_title_part}.md"
    else:
        # Handle cases where EO number might be missing but title implies it
        eo_match = re.match(r'executive order (\d+)', order['title'], re.IGNORECASE)
        if eo_match:
             filename = f"{date_str}-executive-order-{eo_match.group(1)}-{clean_title_part}.md"
        else:
             filename = f"{date_str}-{clean_title_part}.md"


    filepath = os.path.join(dir_path, filename)
    # Prevent overwrite if file exists
    if os.path.exists(filepath):
        print(f"Skipping save for {order['title']} - file already exists: {filepath}")
        return False

    # Format the content using the imported function
    formatted_content = format_content(content)

    # Extract publication date if available, otherwise use signing date
    publication_date_str = order.get('publication_date')
    filed_date_str = order['date'].strftime('%B %d, %Y') # Default to signing date
    if publication_date_str:
        try:
            pub_date = datetime.strptime(publication_date_str, '%Y-%m-%d')
            filed_date_str = pub_date.strftime('%B %d, %Y')
        except ValueError:
            pass # Keep signing date if publication date format is unexpected


    markdown_content = f"""# {order['title']}

## Summary

**Signed:** {order['date'].strftime('%B %d, %Y')}
**Published:** {filed_date_str if publication_date_str else 'N/A'}

**Document Details:**
- Document Number: {order.get('document_number', 'N/A')}
- Executive Order Number: {order.get('eo_number', 'N/A')}
- Citation: {order.get('citation', 'N/A')}

## Sources
- [Federal Register HTML]({order['link']})
- [XML Source]({order.get('xml_url', '#')})
- [PDF Source]({order.get('pdf_url', '#')})

---

## Executive Order {order.get('eo_number', '')}

{formatted_content}

---

*Filed by the Office of the Federal Register on {filed_date_str}*
"""

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print(f"Saved: {filepath}")
        return True
    except OSError as e: # Catch specific file system errors
        print(f"Error saving file {filepath}: {e}")
        return False
    except Exception as e: # Catch other potential errors
        print(f"An unexpected error occurred while saving {filepath}: {e}")
        return False

# Add any other utility functions previously in scrape_new_orders.py if needed