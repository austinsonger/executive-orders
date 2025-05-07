`UPDATED ON:2025-05-07` 

# Executive Orders Scraper


An automated tool that scrapes executive orders from the Federal Register and archives them as markdown files. The scraper runs daily using GitHub Actions to maintain an up-to-date archive of executive orders.

## Features

- Automatically scrapes executive orders from Federal Register
- Converts orders into clean markdown format
- Organizes orders by year in separate directories
- Runs daily via GitHub Actions
- Includes metadata (date, source URL) with each order
- Avoids duplicating existing orders

## Requirements

- Python 3.10 or higher
- Required Python packages (installed via requirements.txt):
  - beautifulsoup4
  - requests
  - python-dateutil

## Setup

1. Clone this repository:
```bash
git clone [repository-url]
cd trumporders
```

2. Create a virtual environment (optional but recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

You can run the scraper manually:

```bash
python scrape_orders.py
```

The script will:
1. Fetch executive orders from the White House website
2. Parse the content and metadata
3. Save new orders as markdown files in the `orders/` directory
4. Skip any orders that have already been archived

## Automated Runs

The project includes a GitHub Actions workflow that:
- Runs the scraper daily at midnight UTC
- Automatically commits and pushes any new orders
- Can be triggered manually through the GitHub Actions interface

## Directory Structure

- `scrape_orders.py` - Main scraping script
- `requirements.txt` - Python dependencies
- `orders/` - Directory containing archived orders (organized by year)
- `.github/workflows/` - GitHub Actions workflow configuration

