#!/usr/bin/env python3
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil import parser
import re

def create_markdown_dir(year):
    """Create directory for the year if it doesn't exist"""
    dir_path = f"orders/{year}"
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    return dir_path

def clean_filename(title):
    """Convert title to valid filename"""
    return re.sub(r'[^\w\s-]', '', title).strip().lower().replace(' ', '-')

def scrape_executive_orders():
    url = "https://www.whitehouse.gov/presidential-actions/executive-orders/"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find all executive order entries
    orders = []
    for article in soup.find_all('article'):
        try:
            title_elem = article.find('h2')
            if not title_elem:
                continue
                
            title = title_elem.text.strip()
            if not "Executive Order" in title:
                continue
                
            date_elem = article.find('time')
            if not date_elem:
                continue
                
            date = parser.parse(date_elem.get('datetime'))
            link = article.find('a')['href']
            
            orders.append({
                'title': title,
                'date': date,
                'link': link
            })
        except Exception as e:
            print(f"Error processing article: {e}")
            continue
    
    return orders

def get_order_content(url):
    """Get the content of an executive order"""
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find the main content
    content = soup.find('div', class_='page-content')
    if not content:
        return None
        
    return content.get_text(separator='\n\n')

def save_as_markdown(order, content):
    """Save the executive order as a markdown file"""
    year = order['date'].year
    dir_path = create_markdown_dir(year)
    
    # Create filename from date and title
    date_str = order['date'].strftime('%Y-%m-%d')
    clean_title = clean_filename(order['title'])
    filename = f"{date_str}-{clean_title}.md"
    filepath = os.path.join(dir_path, filename)
    
    # Don't rewrite if file exists
    if os.path.exists(filepath):
        return False
        
    markdown_content = f"""# {order['title']}

Date: {order['date'].strftime('%B %d, %Y')}

Source: [{order['link']}]({order['link']})

---

{content}
"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    return True

def main():
    # Create base directory if it doesn't exist
    if not os.path.exists('orders'):
        os.makedirs('orders')
        
    orders = scrape_executive_orders()
    new_orders = 0
    
    for order in orders:
        content = get_order_content(order['link'])
        if content and save_as_markdown(order, content):
            new_orders += 1
            print(f"Saved: {order['title']}")
    
    print(f"Processed {len(orders)} orders, {new_orders} new orders saved.")

if __name__ == "__main__":
    main()