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

Usage:
    python crawl_bjx_qn.py

Output:
- articles.json: JSON format with all article data
- articles.csv: CSV format with columns: title, date, url
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
import csv
import sys
import time
import logging
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

# Constants
BASE_URL = 'https://qn.bjx.com.cn/zq'
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
                raise  # Re-raise the last exception

def parse_articles(html: str, base_url: str) -> List[Dict[str, str]]:
    """
    Parse article information from HTML content.
    
    Args:
        html: HTML content to parse
        base_url: Base URL for resolving relative links
        
    Returns:
        List of dictionaries with keys: title, date, url
    """
    articles = []
    
    try:
        soup = BeautifulSoup(html, 'lxml')
        
        # Find the container with class 'cc-list-content'
        container = soup.find('div', class_='cc-list-content')
        if not container:
            logger.error("Could not find container with class 'cc-list-content'")
            return articles
            
        # Find the ul element within the container
        ul_element = container.find('ul')
        if not ul_element:
            logger.error("Could not find ul element within cc-list-content")
            return articles
            
        # Find all li elements
        li_elements = ul_element.find_all('li')
        logger.info(f"Found {len(li_elements)} article items")
        
        for i, li in enumerate(li_elements):
            try:
                # Find the link element
                link = li.find('a')
                if not link:
                    logger.warning(f"No link found in item {i+1}")
                    continue
                
                # Extract title from title attribute or text content
                title = link.get('title', '').strip()
                if not title:
                    title = link.get_text(strip=True)
                
                # Extract URL and make it absolute
                href = link.get('href', '')
                if not href:
                    logger.warning(f"No href found in item {i+1}")
                    continue
                
                url = urljoin(base_url, href)
                
                # Extract date from span element
                date_span = li.find('span')
                date = date_span.get_text(strip=True) if date_span else ''
                
                # Validate extracted data
                if not title or not url:
                    logger.warning(f"Incomplete data for item {i+1}: title='{title}', url='{url}'")
                    continue
                
                article = {
                    'title': title,
                    'date': date,
                    'url': url
                }
                
                articles.append(article)
                logger.debug(f"Extracted article: {article['title'][:50]}...")
                
            except Exception as e:
                logger.error(f"Error parsing item {i+1}: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Error parsing HTML: {e}")
        
    return articles

def get_next_page_url(html: str, base_url: str) -> Optional[str]:
    """
    Extract the URL for the next page if pagination exists.
    
    Args:
        html: HTML content to parse
        base_url: Base URL for resolving relative links
        
    Returns:
        Next page URL if available, None otherwise
    """
    try:
        soup = BeautifulSoup(html, 'lxml')
        
        # Find pagination container
        pagination = soup.find('div', class_='cc-paging')
        if not pagination:
            return None
            
        # Look for "下一页" (next page) link
        next_link = pagination.find('a', string='下一页')
        if not next_link:
            return None
            
        # Check if the next link is disabled
        if 'disable' in next_link.get('class', []):
            return None
            
        href = next_link.get('href')
        if href and href != 'javascript:;':
            return urljoin(base_url, href)
            
    except Exception as e:
        logger.error(f"Error finding next page URL: {e}")
        
    return None

def crawl_all_pages(start_url: str, max_pages: int = 10) -> List[Dict[str, str]]:
    """
    Crawl all pages starting from the given URL.
    
    Args:
        start_url: Starting URL to crawl
        max_pages: Maximum number of pages to crawl (safety limit)
        
    Returns:
        List of all articles from all pages
    """
    all_articles = []
    current_url = start_url
    page_count = 0
    
    while current_url and page_count < max_pages:
        page_count += 1
        logger.info(f"Crawling page {page_count}: {current_url}")
        
        try:
            html = fetch_html(current_url)
            articles = parse_articles(html, current_url)
            
            if not articles:
                logger.warning(f"No articles found on page {page_count}")
            else:
                all_articles.extend(articles)
                logger.info(f"Extracted {len(articles)} articles from page {page_count}")
            
            # Get next page URL
            next_url = get_next_page_url(html, current_url)
            if next_url:
                logger.info(f"Found next page: {next_url}")
                current_url = next_url
                time.sleep(1)  # Be respectful to the server
            else:
                logger.info("No more pages found")
                break
                
        except Exception as e:
            logger.error(f"Error crawling page {page_count}: {e}")
            break
    
    logger.info(f"Crawling completed. Total articles: {len(all_articles)}")
    return all_articles

def save_to_json(articles: List[Dict[str, str]], filename: str = 'articles.json') -> None:
    """Save articles to JSON file."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(articles)} articles to {filename}")
    except Exception as e:
        logger.error(f"Error saving JSON file: {e}")

def save_to_csv(articles: List[Dict[str, str]], filename: str = 'articles.csv') -> None:
    """Save articles to CSV file."""
    try:
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            if articles:
                fieldnames = ['title', 'date', 'url']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(articles)
        logger.info(f"Saved {len(articles)} articles to {filename}")
    except Exception as e:
        logger.error(f"Error saving CSV file: {e}")

def main():
    """Main function to orchestrate the crawling process."""
    try:
        logger.info("Starting BJX QN website crawler...")
        logger.info(f"Target URL: {BASE_URL}")
        
        # Crawl articles from all pages (limiting to first 5 pages for safety)
        articles = crawl_all_pages(BASE_URL, max_pages=5)
        
        if not articles:
            logger.error("No articles were extracted!")
            sys.exit(1)
        
        # Save results in both formats
        save_to_json(articles)
        save_to_csv(articles)
        
        # Print summary
        print(f"\n✅ Successfully crawled {len(articles)} articles")
        print(f"📄 Results saved to:")
        print(f"   - articles.json")
        print(f"   - articles.csv")
        
        # Show first few articles as preview
        if articles:
            print(f"\n🔍 Preview of first 3 articles:")
            for i, article in enumerate(articles[:3], 1):
                print(f"{i}. {article['title'][:60]}...")
                print(f"   Date: {article['date']}")
                print(f"   URL: {article['url']}")
                print()
        
    except KeyboardInterrupt:
        logger.info("Crawling interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
