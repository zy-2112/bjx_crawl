#!/usr/bin/env python3
"""
BJX QN Website Crawler

This script crawls the BJX Hydrogen Energy website (https://qn.bjx.com.cn/zq)
to extract article information including title, date, and URL.

Requirements:
- Python 3.7+
- requests
- beautifulsoup4
- lxml
- openpyxl  # ← for Excel output

Usage:
    python crawl_bjx_qn.py

Output:
- articles.json: JSON format with all article data
- articles.xlsx: Excel format with columns: title, date, url
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import sys
import time
import logging
from typing import List, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

# Constants
BASE_URL = 'https://qn.bjx.com.cn/zq'  # ← Fixed: no trailing spaces!
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

def fetch_html(url: str, timeout: int = 15, retries: int = 3) -> str:
    session = requests.Session()
    session.headers.update(HEADERS)
    
    for attempt in range(retries):
        try:
            logger.info(f"Fetching URL: {url} (attempt {attempt + 1})")
            response = session.get(url, timeout=timeout)
            response.raise_for_status()
            
            content = response.text
            
            if len(content) < 100:
                logger.warning(f"Response too short ({len(content)} chars), may be blocked")
                raise requests.RequestException("Response too short – possible block")
            
            lower_content = content.lower()
            blocking_phrases = [
                'captcha', 'access denied', 'not available', 'request blocked',
                'anti-bot', 'cloudflare', '验证', '拒绝访问', '非法请求', 'robot'
            ]
            if any(phrase in lower_content for phrase in blocking_phrases):
                logger.error(f"Blocking detected. Preview: {content[:200]}")
                raise requests.RequestException("Blocked by target website")

            if 'cc-list-content' not in content:
                logger.warning("Expected container 'cc-list-content' not found")

            return content

        except requests.exceptions.RequestException as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise

def parse_articles(html: str, base_url: str) -> List[Dict[str, str]]:
    articles = []
    try:
        soup = BeautifulSoup(html, 'lxml')
        container = soup.find('div', class_='cc-list-content')
        if not container:
            logger.error("Could not find container with class 'cc-list-content'")
            return articles
            
        ul_element = container.find('ul')
        if not ul_element:
            logger.error("Could not find ul element within cc-list-content")
            return articles
            
        li_elements = ul_element.find_all('li')
        logger.info(f"Found {len(li_elements)} article items")
        
        for i, li in enumerate(li_elements):
            try:
                link = li.find('a')
                if not link:
                    logger.warning(f"No link found in item {i+1}")
                    continue
                
                title = link.get('title', '').strip()
                if not title:
                    title = link.get_text(strip=True)
                
                href = link.get('href', '')
                if not href:
                    logger.warning(f"No href found in item {i+1}")
                    continue
                
                url = urljoin(base_url, href)
                date_span = li.find('span')
                date = date_span.get_text(strip=True) if date_span else ''
                
                if not title or not url:
                    logger.warning(f"Incomplete data for item {i+1}: title='{title}', url='{url}'")
                    continue
                
                articles.append({'title': title, 'date': date, 'url': url})
                logger.debug(f"Extracted article: {title[:50]}...")
                
            except Exception as e:
                logger.error(f"Error parsing item {i+1}: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Error parsing HTML: {e}")
        
    return articles

def get_next_page_url(html: str, base_url: str) -> str:
    try:
        soup = BeautifulSoup(html, 'lxml')
        pagination = soup.find('div', class_='cc-paging')
        if not pagination:
            return None
        next_link = pagination.find('a', string='下一页')
        if not next_link or 'disable' in next_link.get('class', []):
            return None
        href = next_link.get('href')
        if href and href != 'javascript:;':
            return urljoin(base_url, href)
    except Exception as e:
        logger.error(f"Error finding next page URL: {e}")
    return None

def crawl_all_pages(start_url: str, max_pages: int = 5) -> List[Dict[str, str]]:
    all_articles = []
    current_url = start_url
    page_count = 0
    
    while current_url and page_count < max_pages:
        page_count += 1
        logger.info(f"Crawling page {page_count}: {current_url}")
        try:
            html = fetch_html(current_url)
            articles = parse_articles(html, current_url)
            if articles:
                all_articles.extend(articles)
                logger.info(f"Extracted {len(articles)} articles from page {page_count}")
            else:
                logger.warning(f"No articles found on page {page_count}")
            
            next_url = get_next_page_url(html, current_url)
            if next_url:
                logger.info(f"Found next page: {next_url}")
                current_url = next_url
                time.sleep(1)
            else:
                logger.info("No more pages found")
                break
        except Exception as e:
            logger.error(f"Error crawling page {page_count}: {e}")
            break
    
    logger.info(f"Crawling completed. Total articles: {len(all_articles)}")
    return all_articles

def save_to_json(articles: List[Dict[str, str]], filename: str = 'articles.json') -> None:
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(articles)} articles to {filename}")
    except Exception as e:
        logger.error(f"Error saving JSON file: {e}")

# ✅ NEW: Save to Excel (XLSX)
def save_to_xlsx(articles: List[Dict[str, str]], filename: str = 'articles.xlsx') -> None:
    try:
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "BJX Articles"
        
        # Header
        ws.append(['Title', 'Date', 'URL'])
        
        # Data
        for article in articles:
            ws.append([article['title'], article['date'], article['url']])
        
        # Auto-adjust column widths (optional)
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 80)
            ws.column_dimensions[column].width = adjusted_width

        wb.save(filename)
        logger.info(f"Saved {len(articles)} articles to {filename}")
    except Exception as e:
        logger.error(f"Error saving Excel file: {e}")

def main():
    try:
        logger.info("Starting BJX QN website crawler...")
        logger.info(f"Target URL: {BASE_URL}")
        
        articles = crawl_all_pages(BASE_URL, max_pages=5)
        
        if not articles:
            logger.error("No articles were extracted!")
            sys.exit(1)
        
        # ✅ Save to JSON and Excel (not CSV)
        save_to_json(articles)
        save_to_xlsx(articles)  # ← New!
        
        print(f"\n✅ Successfully crawled {len(articles)} articles")
        print(f"📄 Results saved to:")
        print(f"   - articles.json")
        print(f"   - articles.xlsx")  # ← Updated
        
        if articles:
            print(f"\n🔍 Preview of first 3 articles:")
            for i, article in enumerate(articles[:3], 1):
                print(f"{i}. {article['title'][:60]}...")
                print(f"   Date: {article['date']}")
                print(f"   URL: {article['url']}\n")
        
    except KeyboardInterrupt:
        logger.info("Crawling interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
